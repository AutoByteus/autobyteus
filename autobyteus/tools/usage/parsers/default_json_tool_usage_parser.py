# file: autobyteus/autobyteus/tools/usage/parsers/default_json_tool_usage_parser.py
import json
import re
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING, List
import uuid

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class DefaultJsonToolUsageParser(BaseToolUsageParser):
    """
    A default parser for tool usage commands formatted as custom JSON.
    It expects a 'tool' object with 'function' and 'parameters' keys.
    """
    def get_name(self) -> str:
        return "default_json_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        response_text = self._extract_json_from_response(response.content)
        if not response_text:
            return []

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.debug(f"Could not parse extracted text as JSON. Text: {response_text[:200]}")
            return []

        tool_calls_data = []
        if isinstance(data, list):
            tool_calls_data = data
        elif isinstance(data, dict):
            if "tools" in data and isinstance(data.get("tools"), list):
                tool_calls_data = data["tools"]
            else:
                tool_calls_data = [data]
        else:
            return []

        invocations: List[ToolInvocation] = []
        for call_data in tool_calls_data:
            if not isinstance(call_data, dict):
                continue

            tool_block = call_data.get("tool")
            if not isinstance(tool_block, dict):
                continue
            
            tool_name = tool_block.get("function")
            arguments = tool_block.get("parameters")

            if not tool_name or not isinstance(tool_name, str):
                logger.debug(f"Skipping malformed tool block (missing or invalid 'function'): {tool_block}")
                continue
            
            if arguments is None:
                arguments = {}
            
            if not isinstance(arguments, dict):
                logger.debug(f"Skipping tool block with invalid 'parameters' type ({type(arguments)}): {tool_block}")
                continue
            
            # The custom format does not have a tool ID, so a deterministic one will be generated.
            try:
                # Pass id=None to trigger deterministic ID generation.
                tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=None)
                invocations.append(tool_invocation)
            except Exception as e:
                logger.error(f"Unexpected error creating ToolInvocation for tool '{tool_name}': {e}", exc_info=True)
        
        return invocations

    def _extract_json_from_response(self, text: str) -> Optional[str]:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        # Try to find a JSON object or array in the text
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
