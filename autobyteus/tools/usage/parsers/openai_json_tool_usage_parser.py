# file: autobyteus/autobyteus/tools/usage/parsers/openai_json_tool_usage_parser.py
import json
import logging
from typing import TYPE_CHECKING, List, Optional, Any, Dict

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser
from .exceptions import ToolUsageParseException
from ._json_extractor import _find_json_blobs

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class OpenAiJsonToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for tool usage commands formatted in various JSON
    styles commonly produced by OpenAI and similar models.

    This parser is highly flexible and robustly handles multiple formats:
    - A root object with a "tool_calls" or "tools" key containing a list of tool calls.
    - A root object with a single "tool" key.
    - A root object that is itself a single tool call.
    - A raw list of tool calls.
    - Tool call arguments can be either a JSON object or a stringified JSON.
    """
    def get_name(self) -> str:
        return "openai_json_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        response_text = response.content
        invocations: List[ToolInvocation] = []
        
        # Use a robust method to find all potential JSON blobs in the text
        json_blobs = _find_json_blobs(response_text)
        if not json_blobs:
            logger.debug("No valid JSON object could be extracted from the response content.")
            return invocations

        for blob in json_blobs:
            try:
                data = json.loads(blob)
                
                # Determine the structure of the JSON data
                tool_calls_data: List[Dict[str, Any]] = []
                if isinstance(data, list):
                    # Format: [{"function":...}, {"function":...}]
                    tool_calls_data = data
                elif isinstance(data, dict):
                    # Format: {"tool_calls": [...]} or {"tools": [...]}
                    if "tool_calls" in data and isinstance(data["tool_calls"], list):
                        tool_calls_data = data["tool_calls"]
                    elif "tools" in data and isinstance(data["tools"], list):
                        tool_calls_data = data["tools"]
                    # Format: {"tool": {...}}
                    elif "tool" in data and isinstance(data["tool"], dict):
                        tool_calls_data = [data["tool"]]
                    # Format: {"function": ...}
                    else:
                        tool_calls_data = [data]
                
                if not tool_calls_data:
                    logger.debug(f"JSON response does not match any expected tool call format. Content: {blob[:200]}")
                    continue

                for call_data in tool_calls_data:
                    invocation = self._parse_tool_call_object(call_data)
                    if invocation:
                        invocations.append(invocation)

            except json.JSONDecodeError:
                # This can happen if a blob is not a tool call (e.g., just example JSON).
                # We can safely ignore these.
                logger.debug(f"Could not parse extracted text as JSON in {self.get_name()}. Blob: {blob[:200]}")
                continue
            except Exception as e:
                # If we're here, it's likely a valid JSON but with unexpected structure.
                # It's safer to raise this for upstream handling.
                error_msg = f"Unexpected error while parsing JSON blob: {e}. Blob: {blob[:200]}"
                logger.error(error_msg, exc_info=True)
                raise ToolUsageParseException(error_msg, original_exception=e)

        return invocations

    def _parse_tool_call_object(self, call_data: Dict[str, Any]) -> Optional[ToolInvocation]:
        """
        Parses a single tool call object, which can have various structures.
        - {"function": {"name": str, "arguments": str_json_or_dict}}
        - {"name": str, "arguments": dict}
        """
        if not isinstance(call_data, dict):
            logger.debug(f"Skipping non-dictionary item in tool call list: {call_data}")
            return None

        function_data: Optional[Dict] = call_data.get("function")
        if isinstance(function_data, dict):
            # Standard OpenAI format: {"function": {"name": ..., "arguments": ...}}
            tool_name = function_data.get("name")
            arguments_raw = function_data.get("arguments")
        else:
            # Handle flattened format: {"name": ..., "arguments": ...}
            tool_name = call_data.get("name")
            arguments_raw = call_data.get("arguments")

        if not tool_name or not isinstance(tool_name, str):
            logger.debug(f"Skipping malformed tool call (missing or invalid 'name'): {call_data}")
            return None

        arguments: Dict[str, Any]
        if arguments_raw is None:
            arguments = {}
        elif isinstance(arguments_raw, dict):
            # Arguments are already a dictionary
            arguments = arguments_raw
        elif isinstance(arguments_raw, str):
            # Arguments are a stringified JSON
            arg_string = arguments_raw.strip()
            if not arg_string:
                arguments = {}
            else:
                try:
                    parsed_args = json.loads(arg_string)
                    if not isinstance(parsed_args, dict):
                        logger.error(f"Parsed 'arguments' string for tool '{tool_name}' must be a dictionary, but got {type(parsed_args)}.")
                        return None
                    arguments = parsed_args
                except json.JSONDecodeError as e:
                    # If it's a string but not valid JSON, it's a hard error.
                    raise ToolUsageParseException(
                        f"Failed to parse 'arguments' string for tool '{tool_name}': {arguments_raw}",
                        original_exception=e
                    )
        else:
            # Any other type for arguments is invalid
            logger.error(f"Skipping tool call with invalid 'arguments' type. Expected dict or string, got {type(arguments_raw)}: {call_data}")
            return None
                
        try:
            # The ToolInvocation constructor will generate a deterministic ID if 'id' is None.
            tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=None)
            logger.info(f"Successfully parsed OpenAI-style JSON tool invocation for '{tool_name}'.")
            return tool_invocation
        except Exception as e:
            logger.error(f"Unexpected error creating ToolInvocation for tool '{tool_name}': {e}", exc_info=True)
            return None
