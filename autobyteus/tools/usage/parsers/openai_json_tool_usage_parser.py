# file: autobyteus/autobyteus/tools/usage/parsers/openai_json_tool_usage_parser.py
import json
import logging
import re
from typing import TYPE_CHECKING, List, Optional

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class OpenAiJsonToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for tool usage commands formatted in the OpenAI style.
    """
    def get_name(self) -> str:
        return "openai_json_tool_usage_parser"

    def _extract_json_from_response(self, text: str) -> Optional[str]:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        first_brace = text.find('{')
        if first_brace == -1:
            return None

        json_substring = text[first_brace:]
        try:
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
            tool_calls = data.get("tool_calls")
        except (json.JSONDecodeError, AttributeError):
            logger.debug(f"Could not parse extracted text as JSON or find 'tool_calls' key. Text: {response_text[:200]}")
            return invocations

        if not isinstance(tool_calls, list):
            logger.warning(f"Expected 'tool_calls' in JSON to be a list, but got {type(tool_calls)}. Skipping.")
            return invocations

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
                invocations.append(tool_invocation)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse arguments for OpenAI tool call '{tool_name}' (ID: {tool_id}): {e}. Arguments string was: '{arguments_str}'")
            except Exception as e:
                logger.error(f"Unexpected error processing OpenAI tool call in {self.get_name()}: {e}", exc_info=True)
        
        return invocations
