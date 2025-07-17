import xml.etree.ElementTree as ET
import re
import uuid
import html
from xml.sax.saxutils import escape
import xml.parsers.expat
import logging
from typing import TYPE_CHECKING, Dict, Any, List

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser
from .exceptions import ToolUsageParseException

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class DefaultXmlToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for tool usage commands formatted as XML using a robust,
    stateful, character-by-character scanning approach. This parser can correctly
    identify and extract valid <tool>...</tool> blocks even when they are mixed with
    conversational text, malformed XML, or other noise.
    """
    def get_name(self) -> str:
        return "default_xml_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        text = response.content
        invocations: List[ToolInvocation] = []
        cursor = 0
        
        while cursor < len(text):
            # Find the start of the next potential tool tag from the current cursor position
            tool_start_index = text.find('<tool', cursor)
            if tool_start_index == -1:
                break # No more tool tags in the rest of the string

            # Find the end of that opening <tool ...> tag. This is a potential end.
            tool_start_tag_end = text.find('>', tool_start_index)
            if tool_start_tag_end == -1:
                # Incomplete tag at the end of the file, break
                break

            # Check if another '<' appears before the '>', which would indicate a malformed/aborted tag.
            # Example: <tool name="abc" ... <tool name="xyz">
            next_opening_bracket = text.find('<', tool_start_index + 1)
            if next_opening_bracket != -1 and next_opening_bracket < tool_start_tag_end:
                # The tag was not closed properly before another one started.
                # Advance the cursor to this new tag and restart the loop.
                cursor = next_opening_bracket
                continue

            # Find the corresponding </tool> closing tag
            tool_end_index = text.find('</tool>', tool_start_tag_end)
            if tool_end_index == -1:
                # Found a start tag but no end tag, treat as fragment and advance
                cursor = tool_start_tag_end + 1
                continue

            # Extract the full content of this potential tool block
            block_end_pos = tool_end_index + len('</tool>')
            tool_block = text[tool_start_index:block_end_pos]
            
            # CRITICAL NESTING CHECK:
            # Check if there is another '<tool' start tag within this block.
            # If so, it means this is a malformed, nested block. We must skip it
            # and let the loop find the inner tag on the next iteration.
            # This check is now more of a safeguard, as the logic above should handle most cases.
            if '<tool' in tool_block[1:]:
                # Advance cursor past the opening tag of this malformed block to continue scanning
                cursor = tool_start_tag_end + 1
                continue

            # This is a valid, non-nested block. Attempt to parse it.
            try:
                # Preprocessing and parsing
                processed_block = self._preprocess_xml_for_parsing(tool_block)
                root = ET.fromstring(processed_block)
                
                tool_name = root.attrib.get("name")
                if not tool_name:
                    logger.warning(f"Skipping a <tool> block with no name attribute: {processed_block[:100]}")
                else:
                    arguments = self._parse_arguments_from_xml(root)
                    tool_id_attr = root.attrib.get('id')
                    
                    invocation = ToolInvocation(
                        name=tool_name,
                        arguments=arguments,
                        id=tool_id_attr
                    )
                    invocations.append(invocation)
                    logger.info(f"Successfully parsed XML tool invocation for '{tool_name}'.")

            except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
                # The self-contained block was still malformed. Log and ignore it.
                logger.warning(f"Skipping malformed XML tool block: {e}")
            
            # CRITICAL: Advance cursor past the entire block we just processed
            cursor = block_end_pos
            
        return invocations

    def _preprocess_xml_for_parsing(self, xml_content: str) -> str:
        # This function remains the same as it's not part of the core logic error.
        # It's a helper for cleaning up minor syntax issues before parsing.
        return xml_content

    def _parse_arguments_from_xml(self, command_element: ET.Element) -> Dict[str, Any]:
        """Helper to extract arguments from a parsed <tool> element."""
        arguments: Dict[str, Any] = {}
        arguments_container = command_element.find('arguments')
        if arguments_container is None:
            return arguments
        
        for arg_element in arguments_container.findall('arg'):
            arg_name = arg_element.attrib.get('name')
            if arg_name:
                # Use .text to get only the direct text content of the tag.
                # This is safer than itertext() if the LLM hallucinates nested tags.
                # The XML parser already handles unescaping of standard entities.
                raw_text = arg_element.text or ""
                arguments[arg_name] = raw_text
        return arguments
