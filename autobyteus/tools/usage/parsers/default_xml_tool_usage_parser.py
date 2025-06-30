# file: autobyteus/autobyteus/tools/usage/parsers/default_xml_tool_usage_parser.py
import xml.etree.ElementTree as ET
import re
import uuid
from xml.sax.saxutils import escape, unescape
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
    Parses LLM responses for tool usage commands formatted as XML.
    It looks for either a <tools> block (for multiple calls) or a
    single <tool> block.
    """
    def get_name(self) -> str:
        return "default_xml_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        response_text = response.content
        logger.debug(f"{self.get_name()} attempting to parse response (first 500 chars): {response_text[:500]}...")
        
        invocations: List[ToolInvocation] = []
        match = re.search(r"<tools\b[^>]*>.*?</tools\s*>|<tool\b[^>]*>.*?</tool\s*>", response_text, re.DOTALL | re.IGNORECASE)
        if not match:
            logger.debug(f"No <tools> or <tool> block found by {self.get_name()}.")
            return invocations

        xml_content = match.group(0)
        processed_xml = self._preprocess_xml_for_parsing(xml_content)

        try:
            root = ET.fromstring(processed_xml)
            tool_elements = []

            if root.tag.lower() == "tools":
                tool_elements = root.findall('tool')
                if not tool_elements:
                    logger.debug("Found <tools> but no <tool> children.")
                    return invocations
            elif root.tag.lower() == "tool":
                tool_elements = [root]
            else:
                logger.warning(f"Root XML tag is '{root.tag}', not 'tools' or 'tool'. Skipping parsing.")
                return invocations

            for tool_elem in tool_elements:
                tool_name = tool_elem.attrib.get("name")
                # If 'id' is not present in XML, it will be None, triggering deterministic generation.
                tool_id = tool_elem.attrib.get("id")
                arguments = self._parse_arguments_from_xml(tool_elem)

                if tool_name:
                    tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                    invocations.append(tool_invocation)
                else:
                    logger.warning(f"Parsed a <tool> element but its 'name' attribute is missing or empty.")
        
        except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
            error_msg = f"XML parsing error in '{self.get_name()}': {e}. Content: '{processed_xml[:200]}'"
            logger.debug(error_msg)
            # Raise a specific exception to be caught upstream.
            raise ToolUsageParseException(error_msg, original_exception=e)
        
        except Exception as e:
            logger.error(f"Unexpected error in {self.get_name()} processing XML: {e}. XML Content: {xml_content[:200]}", exc_info=True)
            # Also wrap unexpected errors for consistent handling.
            raise ToolUsageParseException(f"Unexpected error during XML parsing: {e}", original_exception=e)

        return invocations

    def _preprocess_xml_for_parsing(self, xml_content: str) -> str:
        """
        Preprocesses raw XML string from an LLM to fix common errors before parsing.
        """
        processed_content = re.sub(
            r'(<arg\s+name\s*=\s*")([^"]+?)>',
            r'\1\2">',
            xml_content,
            flags=re.IGNORECASE
        )
        if processed_content != xml_content:
            logger.debug("Preprocessor fixed a missing quote in an <arg> tag.")

        cdata_sections: Dict[str, str] = {}
        def cdata_replacer(match_obj: re.Match) -> str:
            placeholder = f"__CDATA_PLACEHOLDER_{len(cdata_sections)}__"
            cdata_sections[placeholder] = match_obj.group(0)
            return placeholder

        xml_no_cdata = re.sub(r'<!\[CDATA\[.*?\]\]>', cdata_replacer, processed_content, flags=re.DOTALL)

        def escape_arg_value(match_obj: re.Match) -> str:
            open_tag = match_obj.group(1)
            content = match_obj.group(2)
            close_tag = match_obj.group(3)
            if re.search(r'<\s*/?[a-zA-Z]', content.strip()):
                return f"{open_tag}{content}{close_tag}"
            escaped_content = escape(content) if not content.startswith("__CDATA_PLACEHOLDER_") else content
            return f"{open_tag}{escaped_content}{close_tag}"

        processed_content = re.sub(
            r'(<arg\s+name\s*=\s*"[^"]*"\s*>\s*)(.*?)(\s*</arg\s*>)',
            escape_arg_value,
            xml_no_cdata,
            flags=re.DOTALL | re.IGNORECASE
        )

        for placeholder, original_cdata_tag in cdata_sections.items():
            processed_content = processed_content.replace(placeholder, original_cdata_tag)

        return processed_content

    def _parse_arguments_from_xml(self, command_element: ET.Element) -> Dict[str, Any]:
        arguments: Dict[str, Any] = {}
        arguments_container = command_element.find('arguments')
        if arguments_container is None:
            logger.debug(f"No <arguments> tag found in <tool name='{command_element.attrib.get('name')}'>. No arguments will be parsed.")
            return arguments
        
        for arg_element in arguments_container.findall('arg'):
            arg_name = arg_element.attrib.get('name')
            if arg_name:
                raw_text = "".join(arg_element.itertext())
                unescaped_value = unescape(raw_text)
                arguments[arg_name] = unescaped_value
        return arguments
