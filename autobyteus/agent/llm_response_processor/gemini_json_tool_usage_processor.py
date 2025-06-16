# file: autobyteus/autobyteus/agent/llm_response_processor/gemini_json_tool_usage_processor.py
import json
import logging
import uuid
from typing import TYPE_CHECKING, Dict, Any, Optional

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events import PendingToolInvocationEvent
from .base_processor import BaseLLMResponseProcessor

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class GeminiJsonToolUsageProcessor(BaseLLMResponseProcessor):
    """
    Processes LLM responses for tool usage commands formatted in the Google Gemini style.
    It expects a JSON object with "name" and "args" keys.
    """
    def get_name(self) -> str:
        return "gemini_json_tool_usage"

    async def process_response(self, response: 'CompleteResponse', context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        response_text = self.extract_json_from_response(response.content)
        if not response_text:
            return False

        try:
            parsed_json = json.loads(response_text)
            
            # Gemini may return a list of tool calls
            if isinstance(parsed_json, list):
                tool_calls = parsed_json
            elif isinstance(parsed_json, dict) and 'tool_calls' in parsed_json:
                 tool_calls = parsed_json['tool_calls']
            else:
                tool_calls = [parsed_json] # Wrap single call in a list

            events_enqueued = 0
            for tool_data in tool_calls:
                tool_name = tool_data.get("name")
                arguments = tool_data.get("args")

                if tool_name and isinstance(tool_name, str) and isinstance(arguments, dict):
                    tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=str(uuid.uuid4()))
                    logger.info(f"Agent '{context.agent_id}' ({self.get_name()}) identified Gemini tool invocation: {tool_invocation.name}. Enqueuing event.")
                    tool_event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
                    await context.input_event_queues.enqueue_tool_invocation_request(tool_event)
                    events_enqueued += 1
                else:
                    logger.debug(f"Skipping malformed Gemini tool call data: {tool_data}")

            return events_enqueued > 0

        except json.JSONDecodeError:
            logger.debug(f"Failed to decode JSON for Gemini tool call: {response_text}")
            return False
        except Exception as e:
            logger.error(f"Error processing Gemini tool usage in {self.get_name()} for agent '{context.agent_id}': {e}", exc_info=True)
            return False
    
    def extract_json_from_response(self, text: str) -> Optional[str]:
        # Simple extraction logic for JSON within ```json ... ``` or just the raw string
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        # Fallback for raw JSON
        stripped_text = text.strip()
        if (stripped_text.startswith('{') and stripped_text.endswith('}')) or \
           (stripped_text.startswith('[') and stripped_text.endswith(']')):
            return stripped_text
            
        return None
