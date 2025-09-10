import logging
import re
from typing import TYPE_CHECKING, Dict, Any, List
from dataclasses import dataclass, field

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

# --- State Machine Components for XML Parsing ---

class _ParserState:
    """Abstract base class for a state in our parser's state machine."""
    def handle(self, context: '_ParsingContext') -> '_ParserState':
        raise NotImplementedError

class _ParsingContentState(_ParserState):
    """Handles the accumulation of character data between tags."""
    def handle(self, context: '_ParsingContext') -> '_ParserState':
        if context.is_eof():
            return None # End of stream
        
        char = context.current_char()
        if char == '<':
            context.commit_content_buffer()
            return _ParsingTagState()
        else:
            context.append_to_buffer(char)
            context.advance()
            return self

class _ParsingTagState(_ParserState):
    """Handles the parsing of a tag, from '<' to '>'."""
    def handle(self, context: '_ParsingContext') -> '_ParserState':
        tag_content_end = context.input_string.find('>', context.cursor)
        if tag_content_end == -1:
            # Malformed XML, treat rest of string as content
            context.append_to_buffer(context.input_string[context.cursor:])
            context.cursor = len(context.input_string)
            return _ParsingContentState()

        tag_content = context.input_string[context.cursor + 1 : tag_content_end]
        context.parser.process_tag(tag_content, context)
        
        context.cursor = tag_content_end + 1
        return _ParsingContentState()

@dataclass
class _ParsingContext:
    """Holds the shared state for the parsing process."""
    parser: 'DefaultXmlToolUsageParser'
    input_string: str
    cursor: int = 0
    stack: List[Any] = field(default_factory=list)
    content_buffer: str = ""

    def __post_init__(self):
        self.stack.append(self.parser._StateDict())

    def advance(self):
        self.cursor += 1

    def is_eof(self) -> bool:
        return self.cursor >= len(self.input_string)

    def current_char(self) -> str:
        return self.input_string[self.cursor]

    def append_to_buffer(self, text: str):
        self.content_buffer += text
    
    def commit_content_buffer(self):
        if self.content_buffer:
            self.parser._commit_content(self.stack, self.content_buffer)
            self.content_buffer = ""

# --- Main Parser Class ---

class DefaultXmlToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for tool usage commands formatted as XML using a robust,
    object-oriented state machine. This parser can correctly identify and extract
    valid <tool>...</tool> blocks and recursively parse nested arguments.
    """

    class _StateDict(dict):
        """A dict subclass that can hold state via attributes."""
        pass

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
                    arguments = self._parse_arguments(arguments_xml)
                except Exception as e:
                    logger.error(f"State machine failed to parse arguments for tool '{tool_name}': {e}", exc_info=True)
            
            invocations.append(ToolInvocation(name=tool_name, arguments=arguments))
            i = content_end + len('</tool>')
        
        return invocations

    def _parse_arguments(self, xml_string: str) -> Dict[str, Any]:
        """Drives the state machine to parse the content of an <arguments> tag."""
        context = _ParsingContext(parser=self, input_string=xml_string)
        state: _ParserState = _ParsingContentState()

        while state and not context.is_eof():
            state = state.handle(context)
        
        context.commit_content_buffer() # Commit any trailing content
        return context.stack[0]

    def process_tag(self, tag_content: str, context: _ParsingContext):
        """Determines if a tag is structural and calls the appropriate handler."""
        STRUCTURAL_TAGS = {'arg', '/arg', 'item', '/item'}
        tag_name_peek = tag_content.split(' ')[0].rstrip('/')

        if tag_name_peek in STRUCTURAL_TAGS:
            is_closing = tag_name_peek.startswith('/')
            if is_closing:
                self._handle_closing_tag(context.stack, tag_name_peek[1:])
            else:
                self._handle_opening_tag(context.stack, tag_content)
        else:
            # Not a structural tag, treat the whole thing as content
            context.append_to_buffer(f"<{tag_content}>")
    
    def _commit_content(self, stack, content):
        if not content:
            return

        logger.debug(f"Committing content chunk: '{content}' to stack depth {len(stack)}")
        top = stack[-1]

        if isinstance(top, self._StateDict) and hasattr(top, '_current_key'):
            key = getattr(top, '_current_key')
            existing_value = top.get(key, "")
            top[key] = existing_value + content
            logger.debug(f"  -> Appended to key '{key}'. New parent state: {top}")

    def _handle_opening_tag(self, stack, tag_content):
        logger.debug(f"Handling opening tag: <{tag_content}>")
        parent = stack[-1]
        
        if tag_content.startswith('arg'):
            name_match = re.search(r'name="([^"]+)"', tag_content)
            if name_match and isinstance(parent, dict):
                if hasattr(parent, '_current_key'):
                    delattr(parent, '_current_key')
                arg_name = name_match.group(1)
                new_container = self._StateDict()
                parent[arg_name] = new_container
                stack.append(new_container)
                new_container._current_key = 'value'
                logger.debug(f"  -> Pushed new dict for arg '{arg_name}'. Stack depth: {len(stack)}")

        elif tag_content.startswith('item'):
            if isinstance(parent, self._StateDict):
                grandparent = stack[-2]
                parent_key = next((k for k, v in grandparent.items() if v is parent), None)
                if parent_key:
                    new_list = []
                    grandparent[parent_key] = new_list
                    stack[-1] = new_list
                    parent = new_list
                    logger.debug(f"  -> Converted parent container for '{parent_key}' to a list.")

            if isinstance(parent, list):
                new_item_container = self._StateDict()
                parent.append(new_item_container)
                stack.append(new_item_container)
                new_item_container._current_key = 'value'
                logger.debug(f"  -> Pushed new dict for item. Stack depth: {len(stack)}")
    
    def _handle_closing_tag(self, stack, tag_name):
        if len(stack) > 1:
            top = stack.pop()
            
            if isinstance(top, self._StateDict) and hasattr(top, '_current_key'):
                key = getattr(top, '_current_key')
                if key in top:
                    value = top[key].strip()
                    parent = stack[-1]
                    if isinstance(parent, list):
                        try:
                            idx = parent.index(top)
                            parent[idx] = value
                            logger.debug(f"  -> Collapsed primitive item '{value}' into parent list.")
                        except ValueError:
                            logger.warning("Could not find item to collapse in parent list.")
                    elif isinstance(parent, dict):
                        parent_key = next((k for k, v in parent.items() if v is top), None)
                        if parent_key:
                            parent[parent_key] = value
                            logger.debug(f"  -> Collapsed primitive '{value}' into parent key '{parent_key}'")

            logger.debug(f"  -> Processed closing tag </{tag_name}>. New stack depth: {len(stack)}")
