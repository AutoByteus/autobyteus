# file: autobyteus/autobyteus/tools/usage/parsers/openai_json_tool_usage_parser.py
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
    Parses LLM responses for tool usage commands formatted in the OpenAI style.
    This parser is flexible and can handle multiple formats:
    1. The official OpenAI API format with a 'tool_calls' list.
    2. A raw list of tool call objects.
    3. Simplified tool calls from fine-tuned models (e.g., {"name": "...", "arguments": {...}}).
    4. A single tool call object not wrapped in a list.
    5. Tool calls wrapped in a `{"tool": ...}` structure for prompt consistency.
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

        tool_calls: Optional[List[Any]] = None
        if isinstance(data, dict):
            # Standard OpenAI format: check for 'tool_calls', fallback to 'tools'
            tool_calls = data.get("tool_calls")
            if not isinstance(tool_calls, list):
                tool_calls = data.get("tools")
        elif isinstance(data, list):
            # The entire response is a list of tool calls
            tool_calls = data
            
        if not isinstance(tool_calls, list):
            # Handle the case where a single tool call is returned as a dictionary, not in a list.
            if isinstance(data, dict):
                 # Check for a 'tool' wrapper. If present, the content is the call.
                if "tool" in data and isinstance(data.get("tool"), dict):
                    tool_calls = [data] # The list contains the wrapped object
                # Otherwise, check for standard function/simplified formats.
                elif ('name' in data and 'arguments' in data) or 'function' in data:
                    tool_calls = [data]
        
        if not isinstance(tool_calls, list):
            logger.warning(f"Expected a list of tool calls, but couldn't find one in the response. Data type: {type(data)}. Skipping.")
            return invocations

        for call_data in tool_calls:
            if not isinstance(call_data, dict):
                logger.debug(f"Skipping non-dict item in tool_calls: {call_data}")
                continue

            # Handle if the call is wrapped in a 'tool' key.
            # This makes the parser compatible with the new example format.
            if "tool" in call_data and isinstance(call_data.get("tool"), dict):
                call_data = call_data["tool"]

            # A tool call ID is required for tracking, but the model may not provide one.
            # If it's missing, we generate one.
            tool_id = call_data.get("id") or f"call_{uuid.uuid4().hex}"
            
            # The tool call can be in the full format `{"function": ...}` or a simplified `{"name": ...}`.
            function_data: Optional[Dict] = call_data.get("function")
            if not isinstance(function_data, dict):
                # If 'function' key is missing, assume simplified format where call_data is the function data.
                function_data = call_data
            
            tool_name = function_data.get("name")
            arguments_raw = function_data.get("arguments")

            if not tool_name:
                logger.debug(f"Skipping malformed function data (missing 'name'): {function_data}")
                continue

            arguments: Optional[Dict] = None
            if isinstance(arguments_raw, str):
                try:
                    arguments = json.loads(arguments_raw)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse 'arguments' string for tool '{tool_name}': {arguments_raw}")
                    continue
            elif isinstance(arguments_raw, dict):
                arguments = arguments_raw
            elif arguments_raw is None:
                arguments = {} # Treat missing arguments as an empty dictionary
            else:
                logger.debug(f"Skipping function data with invalid 'arguments' type ({type(arguments_raw)}): {function_data}")
                continue

            if not isinstance(arguments, dict):
                logger.error(f"Parsed arguments for tool '{tool_name}' is not a dictionary. Got: {type(arguments)}")
                continue
                    
            try:
                tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                invocations.append(tool_invocation)
            except Exception as e:
                logger.error(f"Unexpected error creating ToolInvocation for tool '{tool_name}' (ID: {tool_id}): {e}", exc_info=True)
        
        return invocations
