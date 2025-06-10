# file: autobyteus/autobyteus/agent/llm_response_processor/json_tool_usage_processor.py
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

logger = logging.getLogger(__name__)

class JsonToolUsageProcessor(BaseLLMResponseProcessor):
    """
    Processes LLM responses for tool usage commands formatted as JSON.
    If a command is found, it enqueues a PendingToolInvocationEvent.
    """
    def get_name(self) -> str:
        return "json_tool_usage"

    async def process_response(self, response: str, context: 'AgentContext') -> bool:
        logger.debug(f"JsonToolUsageProcessor attempting to process response (first 500 chars): {response[:500]}...")

        json_str = self._extract_json_string(response)
        if not json_str:
            logger.debug("No JSON string could be reliably extracted from the response.")
            return False

        try:
            parsed_json_data = json.loads(json_str)
            tool_call_data = None

            if isinstance(parsed_json_data, list):
                if not parsed_json_data:
                    logger.debug("Parsed JSON is an empty list. No tool call found.")
                    return False
                for item in parsed_json_data:
                    if isinstance(item, dict) and any(key in item for key in ["tool_name", "name", "function", "tool_call", "command"]):
                        tool_call_data = item
                        logger.debug(f"Found potential tool call object in list: {tool_call_data}")
                        break 
                if not tool_call_data:
                    logger.debug("Parsed JSON was a list, but no suitable tool call object found within it.")
                    return False
            elif isinstance(parsed_json_data, dict):
                tool_call_data = parsed_json_data
            else:
                logger.debug(f"Parsed JSON content is not a dictionary or list of dictionaries: {type(parsed_json_data)}")
                return False

            tool_invocation = self._convert_dict_to_tool_invocation(tool_call_data) 

            if tool_invocation.is_valid():
                logger.info(f"Agent '{context.agent_id}' ({self.get_name()}) identified tool invocation: {tool_invocation.name} (ID: {tool_invocation.id}), args: {tool_invocation.arguments}. Enqueuing event.")
                tool_event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
                # MODIFIED: Use context.input_event_queues
                await context.input_event_queues.enqueue_tool_invocation_request(tool_event) 
                return True
            else:
                logger.debug(f"Agent '{context.agent_id}' ({self.get_name()}) converted JSON to ToolInvocation, but it was invalid.")

        except json.JSONDecodeError as e:
            logger.debug(f"JSON decoding error for agent '{context.agent_id}' by {self.get_name()}: {e}. Invalid JSON string was: '{json_str}'")
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON tool usage in {self.get_name()} for agent '{context.agent_id}': {e}", exc_info=True)
        
        return False

    def _convert_dict_to_tool_invocation(self, tool_data: Dict[str, Any]) -> ToolInvocation:
        if not isinstance(tool_data, dict):
            logger.debug(f"Data for tool invocation is not a dictionary: {type(tool_data)}")
            return ToolInvocation() 

        tool_name: Optional[str] = None
        arguments_obj: Optional[Any] = None
        tool_id: Optional[str] = tool_data.get("id") 

        if "tool_name" in tool_data: 
            tool_name = tool_data.get("tool_name")
            arguments_obj = tool_data.get("arguments", tool_data.get("input"))
        elif "name" in tool_data and ("arguments" in tool_data or "input" in tool_data): 
            tool_name = tool_data.get("name")
            arguments_obj = tool_data.get("arguments", tool_data.get("input"))
        elif "function" in tool_data and isinstance(tool_data["function"], dict): 
            tool_name = tool_data["function"].get("name")
            arguments_obj = tool_data["function"].get("arguments")
        elif "tool_call" in tool_data and isinstance(tool_data["tool_call"], dict): 
            nested_call = tool_data["tool_call"]
            if "function" in nested_call and isinstance(nested_call["function"], dict):
                 tool_name = nested_call["function"].get("name")
                 arguments_obj = nested_call["function"].get("arguments")
            else: 
                 tool_name = nested_call.get("name")
                 arguments_obj = nested_call.get("arguments")
        elif "command" in tool_data and isinstance(tool_data["command"], dict): 
            tool_name = tool_data["command"].get("name")
            arguments_obj = tool_data["command"].get("arguments")
        
        if not tool_name or not isinstance(tool_name, str):
            logger.debug(f"Could not extract a valid string 'tool_name' from JSON data. Found keys: {list(tool_data.keys())}")
            return ToolInvocation(id=tool_id if tool_id else str(uuid.uuid4())) 

        arguments: Dict[str, Any] = {}
        if isinstance(arguments_obj, str): 
            try:
                arguments = json.loads(arguments_obj)
                if not isinstance(arguments, dict):
                    logger.warning(f"Successfully parsed 'arguments' string, but it's not a dict: {type(arguments)}. String was: {arguments_obj}")
                    return ToolInvocation(name=tool_name, id=tool_id if tool_id else str(uuid.uuid4())) 
            except json.JSONDecodeError:
                logger.debug(f"Field 'arguments' is a string but not valid JSON: '{arguments_obj}'. Invalid arguments for tool '{tool_name}'.")
                return ToolInvocation(name=tool_name, id=tool_id if tool_id else str(uuid.uuid4())) 
        elif isinstance(arguments_obj, dict):
            arguments = arguments_obj
        elif arguments_obj is None: 
            arguments = {}
        else: 
            logger.debug(f"Unsupported type for 'arguments': {type(arguments_obj)}. Expected dict or JSON string. Tool: '{tool_name}'")
            return ToolInvocation(name=tool_name, id=tool_id if tool_id else str(uuid.uuid4()))

        final_id = tool_id if tool_id else str(uuid.uuid4())
        return ToolInvocation(name=tool_name, arguments=arguments, id=final_id)

    def _extract_json_string(self, response: str) -> Optional[str]:
        code_block_match = re.search(r"```(?:json)?\s*([\{\[].*?[\]\}])\s*```", response, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            json_content = code_block_match.group(1).strip()
            if (json_content.startswith('{') and json_content.endswith('}')) or \
               (json_content.startswith('[') and json_content.endswith(']')):
                try:
                    json.loads(json_content) 
                    return json_content
                except json.JSONDecodeError:
                    logger.debug(f"Extracted content from code block, but it's not valid JSON: {json_content[:200]}")
                    pass 

        stripped_response = response.strip()
        if (stripped_response.startswith('{') and stripped_response.endswith('}')) or \
           (stripped_response.startswith('[') and stripped_response.endswith(']')):
            try:
                json.loads(stripped_response) 
                return stripped_response
            except json.JSONDecodeError:
                pass 

        last_curly = stripped_response.rfind('{')
        last_square = stripped_response.rfind('[')
        
        potential_starts = []
        if last_curly != -1: potential_starts.append(last_curly)
        if last_square != -1: potential_starts.append(last_square)

        if not potential_starts: return None

        for start_index in sorted(potential_starts, reverse=True):
            substring_to_test = stripped_response[start_index:]
            try:
                json.loads(substring_to_test) 
                return substring_to_test
            except json.JSONDecodeError:
                pass 
        
        return None
