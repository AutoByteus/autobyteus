import logging
import re
from typing import TYPE_CHECKING, Dict, Any, List
from dataclasses import dataclass, field

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

# A unique UUID to use as an internal key for storing text content.
# This prevents any potential collision with user-provided argument names.
_INTERNAL_TEXT_KEY_UUID = "4e1a3b1e-3b2a-4d3c-9a8b-2a1c2b3d4e5f"

# --- Internal Arguments Parser with State Machine ---
# This entire section is now encapsulated in its own class for clarity.

class _XmlArgumentsParser:
    """
    A dedicated parser for the XML content within an <arguments> tag.
    It encapsulates the state machine and all related logic, separating it
    from the higher-level tool-finding logic.
    """
    
    # --- Nested State Machine Components ---

    @dataclass
    class _ParsingContext:
        """Holds the shared state for the parsing process."""
        parser: '_XmlArgumentsParser'
        input_string: str
        cursor: int = 0
        stack: List[Any] = field(default_factory=list)
        content_buffer: str = ""

        def __post_init__(self):
            self.stack.append({}) # Root of arguments is a dictionary

        def is_eof(self) -> bool:
            return self.cursor >= len(self.input_string)

        def append_to_buffer(self, text: str):
            self.content_buffer += text
        
        def commit_content_buffer(self):
            if self.content_buffer:
                self.parser._commit_content(self.stack, self.content_buffer)
                self.content_buffer = ""

    class _ParserState:
        """Abstract base class for a state in our parser's state machine."""
        def handle(self, context: '_XmlArgumentsParser._ParsingContext') -> '_XmlArgumentsParser._ParserState':
            raise NotImplementedError

    class _ParsingContentState(_ParserState):
        """Handles accumulation of character data between tags."""
        def handle(self, context: '_XmlArgumentsParser._ParsingContext') -> '_XmlArgumentsParser._ParserState':
            if context.is_eof():
                return None
            
            next_tag_start = context.input_string.find('<', context.cursor)

            if next_tag_start == -1:
                context.append_to_buffer(context.input_string[context.cursor:])
                context.cursor = len(context.input_string)
                return self
            
            is_valid_tag = False
            if next_tag_start + 1 < len(context.input_string):
                next_char = context.input_string[next_tag_start + 1]
                if next_char.isalpha() or next_char == '/':
                    is_valid_tag = True
            
            if is_valid_tag:
                content_before_tag = context.input_string[context.cursor:next_tag_start]
                context.append_to_buffer(content_before_tag)
                context.commit_content_buffer()
                context.cursor = next_tag_start
                return self.parser._ParsingTagState(self.parser)
            else:
                content_with_char = context.input_string[context.cursor : next_tag_start + 1]
                context.append_to_buffer(content_with_char)
                context.cursor = next_tag_start + 1
                return self

        def __init__(self, parser: '_XmlArgumentsParser'):
            self.parser = parser

    class _ParsingTagState(_ParserState):
        """Handles parsing of a tag, from '<' to '>'."""
        def handle(self, context: '_XmlArgumentsParser._ParsingContext') -> '_XmlArgumentsParser._ParserState':
            tag_content_end = context.input_string.find('>', context.cursor)
            if tag_content_end == -1:
                context.append_to_buffer(context.input_string[context.cursor:])
                context.cursor = len(context.input_string)
                return self.parser._ParsingContentState(self.parser)

            tag_content = context.input_string[context.cursor + 1 : tag_content_end]
            context.parser.process_tag(tag_content, context)
            
            context.cursor = tag_content_end + 1
            return self.parser._ParsingContentState(self.parser)

        def __init__(self, parser: '_XmlArgumentsParser'):
            self.parser = parser

    # --- Parser Implementation ---
    
    def __init__(self, xml_string: str):
        self.xml_string = xml_string

    def parse(self) -> Dict[str, Any]:
        """Drives the state machine to parse the XML string."""
        context = self._ParsingContext(parser=self, input_string=self.xml_string)
        state = self._ParsingContentState(self)

        while state and not context.is_eof():
            state = state.handle(context)
        
        context.commit_content_buffer()
        
        final_args = context.stack[0]
        self._cleanup_internal_keys(final_args)
        return final_args

    def process_tag(self, tag_content: str, context: '_ParsingContext'):
        STRUCTURAL_TAGS = {'arg', 'item'}
        stripped_content = tag_content.strip()
        if not stripped_content:
            context.append_to_buffer(f"<{tag_content}>")
            return

        is_closing = stripped_content.startswith('/')
        tag_name = (stripped_content[1:] if is_closing else stripped_content).split(' ')[0]

        if tag_name in STRUCTURAL_TAGS:
            if is_closing:
                self._handle_closing_tag(context.stack)
            else:
                self._handle_opening_tag(context.stack, tag_content)
        else:
            context.append_to_buffer(f"<{tag_content}>")
    
    def _commit_content(self, stack: List[Any], content: str):
        trimmed_content = content.strip()
        if not trimmed_content and '<' not in content and '>' not in content:
            return

        top = stack[-1]
        if isinstance(top, dict):
            top[_INTERNAL_TEXT_KEY_UUID] = top.get(_INTERNAL_TEXT_KEY_UUID, '') + content

    def _handle_opening_tag(self, stack: List[Any], tag_content: str):
        parent = stack[-1]
        
        if tag_content.strip().startswith('arg'):
            name_match = re.search(r'name="([^"]+)"', tag_content)
            if name_match and isinstance(parent, dict):
                arg_name = name_match.group(1)
                new_container = {}
                parent[arg_name] = new_container
                stack.append(new_container)
        
        elif tag_content.strip().startswith('item'):
            if isinstance(parent, dict):
                grandparent = stack[-2]
                parent_key = next((k for k, v in grandparent.items() if v is parent), None)
                if parent_key:
                    new_list = []
                    grandparent[parent_key] = new_list
                    stack[-1] = new_list
                    parent = new_list
            
            if isinstance(parent, list):
                new_item_container = {}
                parent.append(new_item_container)
                stack.append(new_item_container)

    def _handle_closing_tag(self, stack: List[Any]):
        if len(stack) > 1:
            top = stack.pop()
            parent = stack[-1]

            is_primitive = False
            if isinstance(top, dict):
                keys = top.keys()
                if not keys or (len(keys) == 1 and _INTERNAL_TEXT_KEY_UUID in keys):
                    is_primitive = True

            if is_primitive:
                value = top.get(_INTERNAL_TEXT_KEY_UUID, '')
                if isinstance(parent, list):
                    try:
                        idx = parent.index(top)
                        parent[idx] = value
                    except ValueError:
                        logger.warning("Could not find item to collapse in parent list.")
                elif isinstance(parent, dict):
                    parent_key = next((k for k, v in parent.items() if v is top), None)
                    if parent_key:
                        parent[parent_key] = value

    def _cleanup_internal_keys(self, data: Any):
        if isinstance(data, dict):
            if _INTERNAL_TEXT_KEY_UUID in data and len(data) > 1:
                del data[_INTERNAL_TEXT_KEY_UUID]
            for value in data.values():
                self._cleanup_internal_keys(value)
        elif isinstance(data, list):
            for item in data:
                self._cleanup_internal_keys(item)


# --- Main Parser Class ---

class DefaultXmlToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for tool usage commands formatted as XML.
    This class is responsible for finding <tool> blocks and delegating the
    parsing of their arguments to the specialized _XmlArgumentsParser.
    """

    def get_name(self) -> str:
        return "default_xml_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        text = response.content
        invocations: List[ToolInvocation] = []
        i = 0

        while i < len(text):
            try:
                i = text.index('<tool', i)
            except ValueError:
                break

            open_tag_end = text.find('>', i)
            if open_tag_end == -1: break

            open_tag_content = text[i:open_tag_end+1]
            name_match = re.search(r'name="([^"]+)"', open_tag_content)
            if not name_match:
                i = open_tag_end + 1
                continue
            
            tool_name = name_match.group(1)
            logger.debug(f"--- Found tool '{tool_name}' at index {i} ---")

            cursor = open_tag_end + 1
            nesting_level = 1
            content_end = -1
            
            while cursor < len(text):
                next_open = text.find('<tool', cursor)
                next_close = text.find('</tool>', cursor)

                if next_close == -1: break

                if next_open != -1 and next_open < next_close:
                    nesting_level += 1
                    end_of_nested_open = text.find('>', next_open)
                    if end_of_nested_open == -1: break
                    cursor = end_of_nested_open + 1
                else:
                    nesting_level -= 1
                    if nesting_level == 0:
                        content_end = next_close
                        break
                    cursor = next_close + len('</tool>')
            
            if content_end == -1:
                logger.warning(f"Malformed XML for tool '{tool_name}': could not find matching </tool> tag.")
                i = open_tag_end + 1
                continue

            tool_content = text[open_tag_end+1:content_end]
            args_match = re.search(r'<arguments>(.*)</arguments>', tool_content, re.DOTALL)
            
            arguments = {}
            if args_match:
                arguments_xml = args_match.group(1)
                try:
                    # Delegate parsing to the specialized class
                    arguments = self._parse_arguments(arguments_xml)
                except Exception as e:
                    logger.error(f"Arguments parser failed for tool '{tool_name}': {e}", exc_info=True)
            
            invocations.append(ToolInvocation(name=tool_name, arguments=arguments))
            i = content_end + len('</tool>')
        
        return invocations

    def _parse_arguments(self, xml_string: str) -> Dict[str, Any]:
        """
        Delegates parsing of an arguments XML string to the dedicated parser class.
        """
        parser = _XmlArgumentsParser(xml_string)
        return parser.parse()

