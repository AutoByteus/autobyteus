# file: autobyteus/autobyteus/agent/llm_response_processor/xml_tool_usage_processor.py
import xml.etree.ElementTree as ET
import re
import uuid # For generating tool invocation IDs
from xml.sax.saxutils import escape, unescape
import xml.parsers.expat
import logging
from typing import TYPE_CHECKING, Dict, Any

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events import PendingToolInvocationEvent # MODIFIED IMPORT
from .base_processor import BaseLLMResponseProcessor # Relative import, OK

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class XmlToolUsageProcessor(BaseLLMResponseProcessor):
    """
    Processes LLM responses for tool usage commands formatted as XML.
    If a command is found, it enqueues a PendingToolInvocationEvent.
    Expected format:
    <command id="optional_tool_call_id" name="tool_name">
        <arg name="arg1_name">arg1_value</arg>
        <arg name="arg2_name">arg2_value</arg>
    </command>
    """
    @classmethod
    def get_name(cls) -> str:
        return "xml_tool_usage"

    async def process_response(self, response: str, context: 'AgentContext') -> bool:
        logger.debug(f"XmlToolUsageProcessor attempting to process response (first 500 chars): {response[:500]}...")

        # Regex to find <command ...> ... </command> block, case-insensitive for tags
        # It allows attributes within the command tag.
        match = re.search(r"<command\b[^>]*>.*?</command\s*>", response, re.DOTALL | re.IGNORECASE)

        if match:
            xml_content = match.group(0)
            logger.debug(f"Extracted XML content: {xml_content}")

            # Preprocessing to handle potential issues before parsing
            processed_xml = self._preprocess_xml_for_parsing(xml_content)
            logger.debug(f"Preprocessed XML for parsing: {processed_xml}")

            try:
                # Attempt to parse the potentially cleaned XML
                root = ET.fromstring(processed_xml)
                logger.debug(f"Parsed XML root tag: {root.tag}")

                # Ensure the root tag is 'command' (case-insensitive check already done by regex effectively)
                if root.tag.lower() == "command":
                    tool_name = root.attrib.get("name")
                    tool_id = root.attrib.get("id", str(uuid.uuid4())) # Get ID or generate one
                    
                    arguments = self._parse_arguments_from_xml(root)
                    
                    if tool_name: 
                        tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                        logger.info(
                            f"Agent '{context.agent_id}' ({self.get_name()}) identified tool invocation: "
                            f"{tool_invocation.name} (ID: {tool_invocation.id}), args: {tool_invocation.arguments}. Enqueuing event."
                        )
                        tool_event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
                        await context.queues.enqueue_tool_invocation_request(tool_event) # Correct queue method
                        return True
                    else:
                        logger.warning(
                            f"Agent '{context.agent_id}' ({self.get_name()}) parsed XML command "
                            f"but 'name' attribute is missing or empty. XML: {xml_content[:200]}"
                        )
                        
            except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
                # Log the error with the content that failed to parse
                logger.debug(
                    f"XML parsing error for content '{processed_xml[:200]}' by {self.get_name()} "
                    f"for agent '{context.agent_id}': {e}"
                )
            except Exception as e:
                 # Catch any other unexpected errors during processing
                 logger.error(
                     f"Unexpected error in {self.get_name()} processing XML for agent '{context.agent_id}': {e}. "
                     f"XML Content: {xml_content[:200]}", exc_info=True
                 )

        logger.debug(f"No valid XML <command> found and processed by {self.get_name()} for agent '{context.agent_id}'.")
        return False

    def _preprocess_xml_for_parsing(self, xml_content: str) -> str:
        """
        Prepares XML content for robust parsing.
        - Escapes content within <arg> tags to prevent it from being interpreted as XML.
        - Handles CDATA sections by temporarily replacing them.
        """
        # Store CDATA sections and replace them with placeholders
        cdata_sections: Dict[str, str] = {}
        def cdata_replacer(match_obj: re.Match) -> str:
            placeholder = f"__CDATA_PLACEHOLDER_{len(cdata_sections)}__"
            cdata_sections[placeholder] = match_obj.group(0) # Store the full CDATA tag
            return placeholder

        xml_no_cdata = re.sub(r'<!\[CDATA\[.*?\]\]>', cdata_replacer, xml_content, flags=re.DOTALL)

        # Escape content ONLY within <arg name="...">...</arg> tags
        # This regex captures the opening tag, the content, and the closing tag of <arg>
        def escape_arg_value(match_obj: re.Match) -> str:
            open_tag = match_obj.group(1)  # e.g., <arg name="query">
            content = match_obj.group(2) # Content between arg tags
            close_tag = match_obj.group(3) # e.g., </arg>
            
            # Escape the content if it's not already a CDATA placeholder
            if not content.startswith("__CDATA_PLACEHOLDER_"):
                escaped_content = escape(content)
            else:
                escaped_content = content # Keep placeholder as is
            return f"{open_tag}{escaped_content}{close_tag}"

        # Apply escaping to <arg> contents
        # Using re.IGNORECASE for arg tags as well
        processed_content = re.sub(
            r'(<arg\s+name\s*=\s*"[^"]*"\s*>\s*)(.*?)(\s*</arg\s*>)',
            escape_arg_value,
            xml_no_cdata,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Restore CDATA sections (now their content is effectively protected)
        for placeholder, original_cdata_tag in cdata_sections.items():
            processed_content = processed_content.replace(placeholder, original_cdata_tag)
            
        return processed_content

    def _parse_arguments_from_xml(self, command_element: ET.Element) -> Dict[str, Any]:
        """
        Parses <arg> elements within a <command> element into a dictionary.
        It unescapes the text content of each <arg> and handles CDATA.
        """
        arguments: Dict[str, Any] = {}
        for arg_element in command_element.findall('arg'): # Case-sensitive findall, ensure <arg> is used
            arg_name = arg_element.attrib.get('name')
            if arg_name:
                # Extract text, including from CDATA if ET.fromstring handles it correctly after preprocessing
                # For ET, text from CDATA is usually mixed in if not stripped.
                # itertext() concatenates all text nodes, which is good for mixed content.
                raw_text_parts = list(arg_element.itertext())
                raw_text = "".join(raw_text_parts).strip()

                # Check if raw_text is a CDATA section and extract content
                cdata_match = re.match(r'<!\[CDATA\[(.*?)\]\]>', raw_text, re.DOTALL)
                if cdata_match:
                    unescaped_value = cdata_match.group(1) # Content of CDATA is not XML-escaped
                else:
                    unescaped_value = unescape(raw_text) # Unescape if it was escaped text

                arguments[arg_name] = unescaped_value
        return arguments
