"""
XmlToolParsingState: Parses <tool name="...">...</tool> blocks.

This state handles tool call parsing, extracting tool name and arguments.
"""
import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Optional, Dict, Any

from .delimited_content_state import DelimitedContentState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlToolParsingState(DelimitedContentState):
    """
    Parses tool call blocks.
    
    Expected format: <tool name="..."><arg>value</arg></tool>
    
    Supports two argument formats:
    1. Wrapped: <arguments><arg1>value1</arg1></arguments>
    2. Direct: <arg1>value1</arg1><arg2>value2</arg2>
    
    The state:
    1. Extracts tool name from the opening tag
    2. Parses arguments within the content
    3. Emits SEGMENT_START with tool metadata
    4. Streams raw content for real-time display
    5. Emits SEGMENT_END when </tool> is found
    """
    
    # Pattern to extract tool name
    NAME_PATTERN = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    CLOSING_TAG = "</tool>"
    SEGMENT_TYPE = SegmentType.TOOL_CALL
    ARGS_OPEN = "<arguments>"
    ARGS_CLOSE = "</arguments>"
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the tool parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The complete opening tag (e.g., '<tool name="read_file">').
        """
        super().__init__(context, opening_tag)
        self._tool_name: Optional[str] = None
        self._parsed_arguments: Dict[str, Any] = {}
        
        # Extract tool name from opening tag
        match = self.NAME_PATTERN.search(opening_tag)
        if match:
            self._tool_name = match.group(1)

    def _can_start_segment(self) -> bool:
        return self._tool_name is not None

    def _get_start_metadata(self) -> dict:
        return {"tool_name": self._tool_name} if self._tool_name else {}

    def _on_segment_complete(self) -> None:
        content = self.context.get_current_segment_content()
        self._parse_arguments_from_content(content)
        self.context.update_current_segment_metadata(
            arguments=self._parsed_arguments
        )

    def _parse_arguments_from_content(self, content: str) -> None:
        """
        Parse XML arguments from the content.

        Supports:
        1) <arguments><arg name="x">...</arg></arguments>
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

    # finalize inherited from DelimitedContentState
