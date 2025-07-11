import json
import logging
import re
import uuid
from typing import TYPE_CHECKING, List, Optional, Any, Dict

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class OpenAiJsonToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for tool usage commands formatted in a strict, dual-standard
    JSON format specific to OpenAI models.

    This parser adheres to two distinct formats:
    1.  **Single Tool Call**: A JSON object with a top-level "tool" key.
        ```json
        {
          "tool": {
            "function": {
              "name": "tool_name",
              "arguments": "{\\"arg1\\":\\"value1\\"}"
            }
          }
        }
        ```
    2.  **Multiple Tool Calls**: A JSON object with a top-level "tools" key
        containing a list of tool call objects.
        ```json
        {
          "tools": [
            {
              "function": {
                "name": "tool_one",
                "arguments": "{\\"argA\\":\\"valueA\\"}"
              }
            },
            {
              "function": {
                "name": "tool_two",
                "arguments": "{\\"argB\\":\\"valueB\\"}"
              }
            }
          ]
        }
        ```
    The 'arguments' field must be a stringified JSON. The parser will not
    process other formats.
    """
    def get_name(self) -> str:
        return "openai_json_tool_usage_parser"

    def _extract_json_from_response(self, text: str) -> Optional[str]:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        # Try to find a JSON object or array
        first_bracket = text.find('[')
        first_brace = text.find('{')

        if first_brace == -1 and first_bracket == -1:
            return None

        start_index = -1
        if first_bracket != -1 and first_brace != -1:
            start_index = min(first_bracket, first_brace)
        elif first_bracket != -1:
            start_index = first_bracket
        else: # first_brace != -1
            start_index = first_brace

        json_substring = text[start_index:]
        try:
            # Check if the substring is valid JSON
            json.loads(json_substring)
            return json_substring
        except json.JSONDecodeError:
            logger.debug(f"Found potential start of JSON, but substring was not valid: {json_substring[:100]}")
            return None

    def _parse_tool_call_object(self, call_data: Dict[str, Any]) -> Optional[ToolInvocation]:
        """
        Parses a single tool call object.

        The object is expected to be in the format:
        `{"function": {"name": str, "arguments": str_json}}`

        Args:
            call_data: A dictionary representing a single tool call.

        Returns:
            A ToolInvocation object if parsing is successful, otherwise None.
        """
        function_data: Optional[Dict] = call_data.get("function")
        if not isinstance(function_data, dict):
            logger.debug(f"Skipping malformed tool call (missing or invalid 'function' object): {call_data}")
            return None
        
        tool_name = function_data.get("name")
        if not tool_name or not isinstance(tool_name, str):
            logger.debug(f"Skipping malformed function data (missing or invalid 'name'): {function_data}")
            return None

        arguments_raw = function_data.get("arguments")

        # Per spec, arguments MUST be a stringified JSON.
        if not isinstance(arguments_raw, str):
            logger.debug(f"Skipping function data with invalid 'arguments' type. Expected string, got {type(arguments_raw)}: {function_data}")
            return None

        # Now we know arguments_raw is a string.
        arguments: Dict[str, Any]
        arg_string = arguments_raw.strip()

        if not arg_string:
            # An empty string for arguments is valid and means no arguments.
            arguments = {}
        else:
            try:
                parsed_args = json.loads(arg_string)
                if not isinstance(parsed_args, dict):
                    logger.error(f"Parsed 'arguments' for tool '{tool_name}' must be a dictionary, but got {type(parsed_args)}.")
                    return None
                arguments = parsed_args
            except json.JSONDecodeError:
                logger.error(f"Failed to parse 'arguments' string for tool '{tool_name}': {arguments_raw}")
                return None
                
        try:
            # The ToolInvocation constructor will generate a deterministic ID if 'id' is None.
            tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=None)
            return tool_invocation
        except Exception as e:
            logger.error(f"Unexpected error creating ToolInvocation for tool '{tool_name}': {e}", exc_info=True)
            return None

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        invocations: List[ToolInvocation] = []
        response_text = self._extract_json_from_response(response.content)
        if not response_text:
            logger.debug("No valid JSON object could be extracted from the response content.")
            return invocations

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.debug(f"Could not parse extracted text as JSON. Text: {response_text[:200]}")
            return invocations

        if not isinstance(data, dict):
            logger.debug(f"Expected a JSON object at the root, but got {type(data)}. Content: {response_text[:200]}")
            return invocations

        has_tool_key = "tool" in data
        has_tools_key = "tools" in data

        if has_tool_key and has_tools_key:
            logger.warning(f"Ambiguous tool call format. Both 'tool' and 'tools' keys are present. Skipping. Content: {response_text[:200]}")
            return invocations

        if has_tool_key:
            # SINGLE tool call format: {"tool": {...}}
            tool_call_data = data.get("tool")
            if not isinstance(tool_call_data, dict):
                logger.warning(f"Invalid single tool call format. 'tool' key must map to an object. Got: {type(tool_call_data)}. Content: {response_text[:200]}")
                return invocations
            
            invocation = self._parse_tool_call_object(tool_call_data)
            if invocation:
                invocations.append(invocation)

        elif has_tools_key:
            # MULTIPLE tool call format: {"tools": [{...}, {...}]}
            tool_calls_list = data.get("tools")
            if not isinstance(tool_calls_list, list):
                logger.warning(f"Invalid multiple tool call format. 'tools' key must map to a list. Got: {type(tool_calls_list)}. Content: {response_text[:200]}")
                return invocations

            for call_data in tool_calls_list:
                if not isinstance(call_data, dict):
                    logger.debug(f"Skipping non-dict item in 'tools' list: {call_data}")
                    continue
                invocation = self._parse_tool_call_object(call_data)
                if invocation:
                    invocations.append(invocation)
        
        else:
            logger.debug(f"JSON response does not match expected format. Missing 'tool' or 'tools' key. Content: {response_text[:200]}")

        return invocations
