"""
XmlToolParsingState: Parses <tool name="...">...</tool> blocks.

This state handles tool call parsing, extracting tool name and arguments.
"""
import re
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
        
        Supports two formats:
        1. Wrapped: <arguments><arg1>value1</arg1></arguments>
        2. Direct: <arg1>value1</arg1><arg2>value2</arg2>
        """
        # Simple regex-based argument extraction
        args_match = re.search(
            rf'{self.ARGS_OPEN}(.*?){self.ARGS_CLOSE}',
            content,
            re.IGNORECASE | re.DOTALL
        )
        
        if args_match:
            args_content = args_match.group(1)
        else:
            # No <arguments> wrapper - parse directly from content
            args_content = content.strip()
        
        # Extract individual arguments using regex
        arg_pattern = re.compile(r'<(\w+)>(.*?)</\1>', re.DOTALL)
        for match in arg_pattern.finditer(args_content):
            arg_name = match.group(1)
            arg_value = match.group(2).strip()
            self._parsed_arguments[arg_name] = arg_value

    # finalize inherited from DelimitedContentState
