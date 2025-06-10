# file: autobyteus/autobyteus/agent/llm_response_processor/xml_tool_usage_processor.py
import xml.etree.ElementTree as ET
import re
import uuid # For generating tool invocation IDs
from xml.sax.saxutils import escape, unescape
import xml.parsers.expat
import logging
from typing import TYPE_CHECKING, Dict, Any

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events import PendingToolInvocationEvent 
from .base_processor import BaseLLMResponseProcessor 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent

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
    def get_name(self) -> str:
        return "xml_tool_usage"

    async def process_response(self, response: str, context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        """
        Processes the response to find and handle XML tool commands.
        The 'triggering_event' parameter is currently ignored by this processor.
        """
        logger.debug(f"XmlToolUsageProcessor attempting to process response (first 500 chars): {response[:500]}...")

        match = re.search(r"<command\b[^>]*>.*?</command\s*>", response, re.DOTALL | re.IGNORECASE)

        if match:
            xml_content = match.group(0)
            logger.debug(f"Extracted XML content: {xml_content}")

            processed_xml = self._preprocess_xml_for_parsing(xml_content)
            logger.debug(f"Preprocessed XML for parsing: {processed_xml}")

            try:
                root = ET.fromstring(processed_xml)
                logger.debug(f"Parsed XML root tag: {root.tag}")

                if root.tag.lower() == "command":
                    tool_name = root.attrib.get("name")
                    tool_id = root.attrib.get("id", str(uuid.uuid4())) 
                    
                    arguments = self._parse_arguments_from_xml(root)
                    
                    if tool_name: 
                        tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                        logger.info(
                            f"Agent '{context.agent_id}' ({self.get_name()}) identified tool invocation: "
                            f"{tool_invocation.name} (ID: {tool_invocation.id}), args: {tool_invocation.arguments}. Enqueuing event."
                        )
                        tool_event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
                        # MODIFIED: Use context.input_event_queues
                        await context.input_event_queues.enqueue_tool_invocation_request(tool_event) 
                        return True
                    else:
                        logger.warning(
                            f"Agent '{context.agent_id}' ({self.get_name()}) parsed XML command "
                            f"but 'name' attribute is missing or empty. XML: {xml_content[:200]}"
                        )
                        
            except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
                logger.debug(
                    f"XML parsing error for content '{processed_xml[:200]}' by {self.get_name()} "
                    f"for agent '{context.agent_id}': {e}"
                )
            except Exception as e:
                 logger.error(
                     f"Unexpected error in {self.get_name()} processing XML for agent '{context.agent_id}': {e}. "
                     f"XML Content: {xml_content[:200]}", exc_info=True
                 )

        logger.debug(f"No valid XML <command> found and processed by {self.get_name()} for agent '{context.agent_id}'.")
        return False

    def _preprocess_xml_for_parsing(self, xml_content: str) -> str:
        cdata_sections: Dict[str, str] = {}
        def cdata_replacer(match_obj: re.Match) -> str:
            placeholder = f"__CDATA_PLACEHOLDER_{len(cdata_sections)}__"
            cdata_sections[placeholder] = match_obj.group(0) 
            return placeholder

        xml_no_cdata = re.sub(r'<!\[CDATA\[.*?\]\]>', cdata_replacer, xml_content, flags=re.DOTALL)

        def escape_arg_value(match_obj: re.Match) -> str:
            open_tag = match_obj.group(1)  
            content = match_obj.group(2) 
            close_tag = match_obj.group(3) 
            
            if not content.startswith("__CDATA_PLACEHOLDER_"):
                escaped_content = escape(content)
            else:
                escaped_content = content 
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
        for arg_element in command_element.findall('arg'): 
            arg_name = arg_element.attrib.get('name')
            if arg_name:
                text_parts = []
                for text_node in arg_element.itertext():
                    stripped_node_text = text_node.strip()
                    if stripped_node_text: 
                        text_parts.append(stripped_node_text)
                raw_text = "".join(text_parts)
                unescaped_value = unescape(raw_text)
                arguments[arg_name] = unescaped_value
        return arguments
