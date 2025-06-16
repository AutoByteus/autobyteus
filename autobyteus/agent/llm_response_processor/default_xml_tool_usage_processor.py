import xml.etree.ElementTree as ET
import re
import uuid
from xml.sax.saxutils import escape, unescape
import xml.parsers.expat
import logging
from typing import TYPE_CHECKING, Dict, Any, List

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events import PendingToolInvocationEvent
from .base_processor import BaseLLMResponseProcessor

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class DefaultXmlToolUsageProcessor(BaseLLMResponseProcessor):
    """
    Processes LLM responses for tool usage commands formatted as XML.
    It looks for a <tool_calls> block and processes each <tool_call> within it,
    enqueuing a PendingToolInvocationEvent for each valid one found.
    This serves as the default XML processor.
    """
    def get_name(self) -> str:
        return "default_xml_tool_usage"

    async def process_response(self, response: 'CompleteResponse', context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        response_text = response.content
        logger.debug(f"DefaultXmlToolUsageProcessor attempting to process response (first 500 chars): {response_text[:500]}...")

        # Find the <tool_calls> block
        match = re.search(r"<tool_calls\b[^>]*>.*?</tool_calls\s*>", response_text, re.DOTALL | re.IGNORECASE)
        if not match:
            logger.debug(f"No <tool_calls> block found by {self.get_name()} for agent '{context.agent_id}'.")
            return False

        xml_content = match.group(0)
        logger.debug(f"Extracted XML content: {xml_content}")

        processed_xml = self._preprocess_xml_for_parsing(xml_content)
        logger.debug(f"Preprocessed XML for parsing: {processed_xml}")

        events_enqueued = 0
        try:
            root = ET.fromstring(processed_xml)
            if root.tag.lower() != "tool_calls":
                logger.warning(f"Root XML tag is '{root.tag}', not 'tool_calls'. Skipping processing.")
                return False

            tool_call_elements = root.findall('tool_call')
            if not tool_call_elements:
                logger.debug("Found <tool_calls> but no <tool_call> children.")
                return False

            for tool_call_elem in tool_call_elements:
                tool_name = tool_call_elem.attrib.get("name")
                tool_id = tool_call_elem.attrib.get("id", str(uuid.uuid4()))
                arguments = self._parse_arguments_from_xml(tool_call_elem)

                if tool_name:
                    tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                    logger.info(
                        f"Agent '{context.agent_id}' ({self.get_name()}) identified tool invocation: "
                        f"{tool_invocation.name} (ID: {tool_invocation.id}), args: {tool_invocation.arguments}. Enqueuing event."
                    )
                    tool_event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
                    await context.input_event_queues.enqueue_tool_invocation_request(tool_event)
                    events_enqueued += 1
                else:
                    logger.warning(
                        f"Agent '{context.agent_id}' ({self.get_name()}) parsed a <tool_call> element "
                        f"but its 'name' attribute is missing or empty."
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

        return events_enqueued > 0

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
            if re.search(r'<\s*[a-zA-Z]', content.strip()):
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
            arguments_container = command_element
        
        for arg_element in arguments_container.findall('arg'):
            arg_name = arg_element.attrib.get('name')
            if arg_name:
                text_parts = [text_node.strip() for text_node in arg_element.itertext() if text_node.strip()]
                raw_text = "".join(text_parts)
                unescaped_value = unescape(raw_text)
                arguments[arg_name] = unescaped_value
        return arguments
