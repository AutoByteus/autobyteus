# file: autobyteus/autobyteus/agent/llm_response_processor/openai_json_tool_usage_processor.py
import json
import logging
import re
from typing import TYPE_CHECKING, Dict, Any, Optional

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events import PendingToolInvocationEvent
from .base_processor import BaseLLMResponseProcessor

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class OpenAiJsonToolUsageProcessor(BaseLLMResponseProcessor):
    """
    Processes LLM responses for tool usage commands formatted in the OpenAI style.
    It extracts a JSON object from the response content, expects it to contain a 
    'tool_calls' list, and processes each item.
    """
    def get_name(self) -> str:
        return "openai_json_tool_usage"

    def _extract_json_from_response(self, text: str) -> Optional[str]:
        """Extracts a JSON string from a markdown block or from noisy text."""
        # 1. Check for markdown block first
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        # 2. Find the first '{' to handle JSON embedded in text
        first_brace = text.find('{')
        if first_brace == -1:
            return None

        # Assume the rest of the string from the first brace is the JSON part
        json_substring = text[first_brace:]
        try:
            # A simple validation to see if it's parsable
            json.loads(json_substring)
            return json_substring
        except json.JSONDecodeError:
            logger.debug(f"Found potential start of JSON, but substring was not valid: {json_substring[:100]}")
            return None

    async def process_response(self, response: 'CompleteResponse', context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        response_text = self._extract_json_from_response(response.content)
        if not response_text:
            logger.debug("No valid JSON object could be extracted from the response content.")
            return False

        try:
            data = json.loads(response_text)
            tool_calls = data.get("tool_calls")
        except (json.JSONDecodeError, AttributeError):
            logger.debug(f"Could not parse extracted text as JSON or find 'tool_calls' key. Text: {response_text[:200]}")
            return False

        if not isinstance(tool_calls, list):
            logger.warning(f"Expected 'tool_calls' in JSON to be a list, but got {type(tool_calls)}. Skipping.")
            return False

        events_enqueued = 0
        for call_data in tool_calls:
            if not isinstance(call_data, dict):
                logger.debug(f"Skipping non-dict item in tool_calls: {call_data}")
                continue

            tool_id = call_data.get("id")
            function_data = call_data.get("function")
            
            if not tool_id or not isinstance(function_data, dict):
                logger.debug(f"Skipping malformed tool call (missing id or function dict): {call_data}")
                continue
            
            tool_name = function_data.get("name")
            arguments_str = function_data.get("arguments")

            if not tool_name or not isinstance(arguments_str, str):
                logger.debug(f"Skipping malformed function data (missing name or arguments string): {function_data}")
                continue

            try:
                arguments = json.loads(arguments_str)
                if not isinstance(arguments, dict):
                    raise TypeError("Parsed arguments are not a dictionary.")
                    
                tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                logger.info(f"Agent '{context.agent_id}' ({self.get_name()}) identified OpenAI tool invocation: {tool_invocation.name} (ID: {tool_invocation.id}). Enqueuing event.")
                tool_event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
                await context.input_event_queues.enqueue_tool_invocation_request(tool_event)
                events_enqueued += 1

            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse arguments for OpenAI tool call '{tool_name}' (ID: {tool_id}): {e}. Arguments string was: '{arguments_str}'")
            except Exception as e:
                logger.error(f"Unexpected error processing OpenAI tool call in {self.get_name()} for agent '{context.agent_id}': {e}", exc_info=True)
        
        return events_enqueued > 0
