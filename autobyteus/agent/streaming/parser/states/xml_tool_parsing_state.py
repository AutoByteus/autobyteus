"""
XmlToolParsingState: Parses <tool name="...">...</tool> blocks.

This state handles tool call parsing, extracting tool name and arguments.
Implements incremental argument streaming - each CONTENT event includes
the current argument name context and boundary state.
"""
import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlToolParsingState(BaseState):
    """
    Parses tool call blocks with incremental argument streaming.
    
    Expected format: <tool name="..."><arguments><arg name="x">value</arg></arguments></tool>
    
    Key features:
    1. Extracts tool name from the opening tag
    2. Streams content with arg_name context in CONTENT events
    3. Parses arguments at end for the final metadata
    4. Supports optional raw-content markers
    5. Uses holdback buffer to avoid emitting partial tags
    """
    
    # Patterns for parsing
    NAME_PATTERN = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    ARG_OPEN_PATTERN = re.compile(r'<arg\s+name\s*=\s*["\']([^"\']+)["\']\s*>', re.IGNORECASE)
    CLOSING_TAG = "</tool>"
    SEGMENT_TYPE = SegmentType.TOOL_CALL
    ARGS_OPEN = "<arguments>"
    ARGS_CLOSE = "</arguments>"
    ITEM_OPEN = "<item>"
    ITEM_CLOSE = "</item>"
    RAW_START = "__START_CONTENT__"
    RAW_END = "__END_CONTENT__"
    _TAG_SPLIT_PATTERN = re.compile(r"(<[A-Za-z!/][^>]*>)")
    _ENTITY_PATTERN = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")
    _RAW_HOLDBACK = len(RAW_END) - 1
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the tool parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The complete opening tag (e.g., '<tool name="read_file">').
        """
        super().__init__(context)
        self._opening_tag = opening_tag
        self._tool_name: Optional[str] = None
        self._parsed_arguments: Dict[str, Any] = {}
        self._segment_started = False
        
        # Buffer for incremental parsing - only hold back enough to detect partial tags
        self._buffer = ""
        self._full_content_parts: List[str] = []
        self._in_raw_guard = False
        
        # Argument tracking for streaming
        self._current_arg_name: Optional[str] = None
        self._in_arguments = False
        self._arg_stack: list = []  # For nested args
        self._segment_completed = False
        
        # Extract tool name from opening tag
        match = self.NAME_PATTERN.search(opening_tag)
        if match:
            self._tool_name = match.group(1)
    
    def _can_start_segment(self) -> bool:
        return self._tool_name is not None
    
    def _get_start_metadata(self) -> dict:
        return {"tool_name": self._tool_name} if self._tool_name else {}
    
    def run(self) -> None:
        from .text_state import TextState
        
        # Start segment if not already started
        if not self._segment_started:
            if not self._can_start_segment():
                # Tool name not found, emit as text
                self.context.append_text_segment(self._opening_tag)
                self.context.transition_to(TextState(self.context))
                return
            
            self.context.emit_segment_start(self.SEGMENT_TYPE, **self._get_start_metadata())
            self._segment_started = True
        
        if not self.context.has_more_chars():
            return
        
        # Get new content
        available = self.context.consume_remaining()
        self._buffer += available
        
        # Process buffer for tags and content
        self._process_buffer()
        
    def _process_buffer(self) -> None:
        """Process the buffer, emitting content with arg context."""
        from .text_state import TextState
        
        while self._buffer:
            if self._current_arg_name is not None:
                if self._in_raw_guard:
                    end_idx = self._buffer.find(self.RAW_END)
                    if end_idx == -1:
                        if len(self._buffer) > self._RAW_HOLDBACK:
                            safe = self._buffer[:-self._RAW_HOLDBACK]
                            self._emit_arg_delta(safe)
                            self._append_full_text(safe)
                            self._buffer = self._buffer[-self._RAW_HOLDBACK:]
                        return
                    
                    if end_idx > 0:
                        self._emit_arg_delta(self._buffer[:end_idx])
                        self._append_full_text(self._buffer[:end_idx])
                    self._buffer = self._buffer[end_idx + len(self.RAW_END):]
                    if self._buffer.startswith("\n"):
                        self._buffer = self._buffer[1:]
                    self._in_raw_guard = False
                    continue
                
                marker_idx = self._buffer.find(self.RAW_START)
                lt_idx = self._buffer.find("<")
                next_idx = self._min_nonneg(marker_idx, lt_idx)
                if next_idx == -1:
                    holdback = self._raw_start_holdback_len(self._buffer)
                    if holdback:
                        safe = self._buffer[:-holdback]
                        if safe:
                            self._emit_arg_delta(safe)
                            self._append_full_text(safe)
                        self._buffer = self._buffer[-holdback:]
                    else:
                        self._emit_arg_delta(self._buffer)
                        self._append_full_text(self._buffer)
                        self._buffer = ""
                    return
                
                if next_idx > 0:
                    self._emit_arg_delta(self._buffer[:next_idx])
                    self._append_full_text(self._buffer[:next_idx])
                    self._buffer = self._buffer[next_idx:]
                    continue
                
                if marker_idx == 0:
                    self._buffer = self._buffer[len(self.RAW_START):]
                    if self._buffer.startswith("\n"):
                        self._buffer = self._buffer[1:]
                    self._in_raw_guard = True
                    continue
                
                # Buffer starts with '<'
                if self._buffer.lower().startswith("</arg>"):
                    self._append_full_raw("</arg>")
                    self._emit_arg_state("end")
                    self._pop_arg()
                    self._buffer = self._buffer[len("</arg>"):]
                    continue
                
                if self._is_arg_tag_prefix(self._buffer.lower()):
                    end_idx = self._buffer.find(">")
                    if end_idx == -1:
                        return
                    tag_text = self._buffer[:end_idx + 1]
                    self._append_full_raw(tag_text)
                    self._push_arg_from_tag(tag_text)
                    self._buffer = self._buffer[end_idx + 1:]
                    continue
                
                if self._buffer.lower().startswith(self.ITEM_OPEN.lower()):
                    self._append_full_raw(self.ITEM_OPEN)
                    self._buffer = self._buffer[len(self.ITEM_OPEN):]
                    continue
                
                if self._buffer.lower().startswith(self.ITEM_CLOSE.lower()):
                    self._append_full_raw(self.ITEM_CLOSE)
                    self._buffer = self._buffer[len(self.ITEM_CLOSE):]
                    continue
                
                if self._buffer.lower().startswith(self.CLOSING_TAG.lower()):
                    self._close_all_open_args()
                    self._finalize_tool_call()
                    after_tag = self._buffer[len(self.CLOSING_TAG):]
                    if after_tag:
                        self.context.rewind_by(len(after_tag))
                    self._buffer = ""
                    self.context.transition_to(TextState(self.context))
                    self._segment_completed = True
                    return
                
                # Unknown '<' inside arg treated as literal
                self._emit_arg_delta("<")
                self._append_full_text("<")
                self._buffer = self._buffer[1:]
                continue
            
            lt_idx = self._buffer.find("<")
            if lt_idx == -1:
                self._emit_outside_arg(self._buffer)
                self._append_full_text(self._buffer)
                self._buffer = ""
                return
            
            if lt_idx > 0:
                self._emit_outside_arg(self._buffer[:lt_idx])
                self._append_full_text(self._buffer[:lt_idx])
                self._buffer = self._buffer[lt_idx:]
                continue
            
            # Buffer starts with '<' outside arg
            if self._buffer.lower().startswith(self.CLOSING_TAG.lower()):
                self._finalize_tool_call()
                after_tag = self._buffer[len(self.CLOSING_TAG):]
                if after_tag:
                    self.context.rewind_by(len(after_tag))
                self._buffer = ""
                self.context.transition_to(TextState(self.context))
                self._segment_completed = True
                return
            
            if self._buffer.lower().startswith(self.ARGS_OPEN.lower()):
                self._append_full_raw(self.ARGS_OPEN)
                self._buffer = self._buffer[len(self.ARGS_OPEN):]
                self._in_arguments = True
                continue
            
            if self._buffer.lower().startswith(self.ARGS_CLOSE.lower()):
                self._append_full_raw(self.ARGS_CLOSE)
                self._buffer = self._buffer[len(self.ARGS_CLOSE):]
                self._in_arguments = False
                continue
            
            if self._is_arg_tag_prefix(self._buffer.lower()):
                end_idx = self._buffer.find(">")
                if end_idx == -1:
                    return
                tag_text = self._buffer[:end_idx + 1]
                self._append_full_raw(tag_text)
                self._push_arg_from_tag(tag_text)
                self._buffer = self._buffer[end_idx + 1:]
                continue
            
            # Unknown tag/text outside arg
            self._emit_outside_arg("<")
            self._append_full_text("<")
            self._buffer = self._buffer[1:]
    
    def _emit_outside_arg(self, content: str) -> None:
        if content:
            self.context.emit_segment_content(content, arg_name=None)

    def _emit_arg_delta(self, content: str) -> None:
        if content:
            self.context.emit_segment_content(content, arg_name=self._current_arg_name, arg_state="delta")

    def _emit_arg_state(self, state: str) -> None:
        if self._current_arg_name:
            self.context.emit_segment_content("", arg_name=self._current_arg_name, arg_state=state)

    def _push_arg_from_tag(self, tag_text: str) -> None:
        arg_match = self.ARG_OPEN_PATTERN.match(tag_text)
        arg_name = arg_match.group(1) if arg_match else None
        self._arg_stack.append(self._current_arg_name)
        self._current_arg_name = arg_name
        self._emit_arg_state("start")

    def _pop_arg(self) -> None:
        if self._arg_stack:
            self._current_arg_name = self._arg_stack.pop()
        else:
            self._current_arg_name = None
        self._in_raw_guard = False

    def _close_all_open_args(self) -> None:
        while self._current_arg_name is not None:
            self._emit_arg_state("end")
            self._pop_arg()

    def _append_full_raw(self, content: str) -> None:
        if content:
            self._full_content_parts.append(content)

    def _append_full_text(self, content: str) -> None:
        if content:
            self._full_content_parts.append(self._escape_text(content))

    @staticmethod
    def _escape_text(content: str) -> str:
        return (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _min_nonneg(a: int, b: int) -> int:
        if a == -1:
            return b
        if b == -1:
            return a
        return min(a, b)

    def _raw_start_holdback_len(self, buffer: str) -> int:
        max_check = min(len(buffer), len(self.RAW_START) - 1)
        for length in range(max_check, 0, -1):
            if self.RAW_START.startswith(buffer[-length:]):
                return length
        return 0

    @staticmethod
    def _is_arg_tag_prefix(buffer_lower: str) -> bool:
        if not buffer_lower.startswith("<arg"):
            return False
        if len(buffer_lower) == 4:
            return True
        next_char = buffer_lower[4]
        return next_char.isspace() or next_char in {">", "/"}
    
    def _finalize_tool_call(self) -> None:
        """Parse arguments from accumulated content and update metadata."""
        content = "".join(self._full_content_parts)
        self._parse_arguments_from_content(content)
        self.context.update_current_segment_metadata(
            arguments=self._parsed_arguments
        )
        self.context.emit_segment_end()
    
    def finalize(self) -> None:
        """Handle end of stream without closing tag."""
        from .text_state import TextState
        
        remaining = self.context.consume_remaining() if self.context.has_more_chars() else ""
        
        if not self._segment_started:
            text = self._opening_tag + self._buffer + remaining
            if text:
                self.context.append_text_segment(text)
            self.context.transition_to(TextState(self.context))
            return
        
        if remaining:
            self._buffer += remaining
        
        self._process_buffer()
        
        if not self._segment_completed:
            if self._buffer:
                if self._current_arg_name is not None:
                    self._emit_arg_delta(self._buffer)
                    self._append_full_text(self._buffer)
                else:
                    self._emit_outside_arg(self._buffer)
                    self._append_full_text(self._buffer)
            self._buffer = ""
            self._close_all_open_args()
            self._finalize_tool_call()
        
        self.context.transition_to(TextState(self.context))
    
    # ===== Argument parsing methods (unchanged from original) =====
    
    def _parse_arguments_from_content(self, content: str) -> None:
        """
        Parse XML arguments from the content.

        Primary format:
        1) <arguments><arg name="x">...</arg></arguments>

        Legacy fallbacks:
        2) <arguments><path>...</path></arguments>
        3) Direct content without <arguments> wrapper
        """
        args_match = re.search(
            rf'{self.ARGS_OPEN}(.*?){self.ARGS_CLOSE}',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if args_match:
            args_content = args_match.group(1)
        else:
            args_content = content.strip()

        if not args_content:
            return

        try:
            root = ET.fromstring(f"<root>{args_content}</root>")
            self._parsed_arguments = self._parse_xml_children(root)
            return
        except ET.ParseError:
            sanitized = self._sanitize_xml_fragment(args_content)
            try:
                root = ET.fromstring(f"<root>{sanitized}</root>")
                self._parsed_arguments = self._parse_xml_children(root)
                return
            except ET.ParseError:
                # Fall back to legacy regex parsing for malformed XML.
                self._parsed_arguments = self._parse_legacy_arguments(args_content)

    def _parse_xml_children(self, element: ET.Element) -> Dict[str, Any]:
        arguments: Dict[str, Any] = {}
        for child in element:
            name = child.attrib.get("name") or child.tag
            if not name:
                continue
            arguments[name] = self._parse_xml_value(child)
        return arguments

    def _parse_xml_value(self, element: ET.Element) -> Any:
        items = [child for child in element if child.tag == "item"]
        if items:
            return [self._parse_item_value(item) for item in items]

        arg_children = [child for child in element if child.tag == "arg"]
        if arg_children:
            return self._parse_xml_children(element)

        other_children = [child for child in element if child.tag not in {"arg", "item"}]
        if other_children:
            return self._parse_xml_children(element)

        text = element.text or ""
        return text.strip()

    def _parse_item_value(self, element: ET.Element) -> Any:
        arg_children = [child for child in element if child.tag == "arg"]
        if arg_children:
            return self._parse_xml_children(element)
        other_children = [child for child in element if child.tag not in {"arg", "item"}]
        if other_children:
            return self._parse_xml_children(element)
        text = element.text or ""
        return text.strip()

    def _parse_legacy_arguments(self, args_content: str) -> Dict[str, Any]:
        arguments: Dict[str, Any] = {}
        arg_pattern = re.compile(r'<(\w+)>(.*?)</\1>', re.DOTALL)
        for match in arg_pattern.finditer(args_content):
            arg_name = match.group(1)
            arg_value = match.group(2).strip()
            arguments[arg_name] = arg_value
        return arguments

    def _sanitize_xml_fragment(self, fragment: str) -> str:
        """Escape raw text to make fragment XML-safe without touching tags."""
        parts = self._TAG_SPLIT_PATTERN.split(fragment)
        sanitized_parts = []
        for part in parts:
            if not part:
                continue
            if part.startswith("<") and part.endswith(">"):
                sanitized_parts.append(part)
                continue
            escaped = self._ENTITY_PATTERN.sub("&amp;", part)
            escaped = escaped.replace("<", "&lt;")
            sanitized_parts.append(escaped)
        return "".join(sanitized_parts)
