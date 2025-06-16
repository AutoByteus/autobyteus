import json
import re
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
import uuid

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events import PendingToolInvocationEvent 
from .base_processor import BaseLLMResponseProcessor 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class DefaultJsonToolUsageProcessor(BaseLLMResponseProcessor):
    """
    A default processor for tool usage commands formatted as JSON.
    This serves as a fallback and attempts a best-effort parsing if no
    provider-specific processor is found.
    """
    def get_name(self) -> str:
        return "default_json_tool_usage"

    async def process_response(self, response: 'CompleteResponse', context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        response_text = self.extract_json_from_response(response.content)
        if not response_text:
            return False

        try:
            parsed_json = json.loads(response_text)
            tool_calls = []

            if isinstance(parsed_json, list):
                tool_calls = parsed_json
            elif isinstance(parsed_json, dict):
                # Handle OpenAI's format as a common fallback
                if "tool_calls" in parsed_json and isinstance(parsed_json["tool_calls"], list):
                    tool_calls = parsed_json["tool_calls"]
                else:
                    tool_calls = [parsed_json]
            else:
                return False

            events_enqueued = 0
            for tool_data in tool_calls:
                if not isinstance(tool_data, dict):
                    continue
                
                function_obj = tool_data.get("function") if isinstance(tool_data.get("function"), dict) else {}
                
                tool_name = tool_data.get("name") or function_obj.get("name")
                
                # Check for args at the top level first, then inside the function object
                args = tool_data.get("arguments")
                if args is None:
                    args = tool_data.get("args")
                if args is None:
                    args = function_obj.get("arguments")
                
                # --- Start of Bug Fix ---
                # A valid tool call MUST have an arguments/args key, even if its value is null or {}.
                # If 'args' is still None after all checks, the key was missing entirely. This is invalid.
                if args is None:
                    logger.debug(f"Skipping tool call because 'arguments' or 'args' key is missing: {tool_data}")
                    continue
                # --- End of Bug Fix ---

                if isinstance(args, str):
                    try:
                        arguments = json.loads(args)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse arguments string in default processor: {args}")
                        continue
                elif isinstance(args, dict):
                    arguments = args
                elif args is None:
                    # This handles the case where the key exists but is explicitly null.
                    arguments = {}
                else:
                    logger.warning(f"Unsupported type for arguments field: {type(args)}. Skipping tool call.")
                    continue

                tool_id = tool_data.get("id", str(uuid.uuid4()))

                if tool_name and isinstance(tool_name, str):
                    invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                    logger.info(f"Agent '{context.agent_id}' ({self.get_name()}) identified tool invocation: {invocation.name}. Enqueuing event.")
                    await context.input_event_queues.enqueue_tool_invocation_request(PendingToolInvocationEvent(tool_invocation=invocation))
                    events_enqueued += 1

            return events_enqueued > 0

        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Default JSON processor failed to parse content: {e}")
            return False

    def extract_json_from_response(self, text: str) -> Optional[str]:
        # 1. Check for markdown block first
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        # 2. Check if the entire string is a JSON object/array
        stripped_text = text.strip()
        if (stripped_text.startswith('{') and stripped_text.endswith('}')) or \
           (stripped_text.startswith('[') and stripped_text.endswith(']')):
            try:
                json.loads(stripped_text)
                return stripped_text
            except json.JSONDecodeError:
                pass # It might be a malformed full string, fall through to substring search

        # 3. Find the first '{' or '[' to handle JSON embedded in text
        first_brace = text.find('{')
        first_bracket = text.find('[')

        start_index = -1

        if first_brace == -1 and first_bracket == -1:
            return None # No JSON found

        if first_brace != -1 and first_bracket != -1:
            start_index = min(first_brace, first_bracket)
        elif first_brace != -1:
            start_index = first_brace
        else: # first_bracket must be != -1
            start_index = first_bracket
            
        json_substring = text[start_index:]
        try:
            # Validate that this substring is valid JSON
            json.loads(json_substring)
            return json_substring
        except json.JSONDecodeError:
            logger.debug(f"Found potential start of JSON, but substring was not valid: {json_substring[:100]}")
            pass
            
        return None
