# file: autobyteus/autobyteus/tools/usage/parsers/gemini_json_tool_usage_parser.py
import json
import logging
from typing import TYPE_CHECKING, List, Dict

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser
from .exceptions import ToolUsageParseException
from ._json_extractor import _find_json_blobs

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class GeminiJsonToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for tool usage commands formatted in the Google Gemini style.
    It expects a JSON object with "name" and "args" keys. It robustly extracts
    all potential JSON objects from the response and can handle both a single
    tool call object or a list of tool call objects.
    """
    def get_name(self) -> str:
        return "gemini_json_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        response_text = response.content
        json_blobs = _find_json_blobs(response_text)
        if not json_blobs:
            return []

        invocations: List[ToolInvocation] = []
        for blob in json_blobs:
            try:
                data = json.loads(blob)
                
                tool_call_list: List[Dict] = []
                if isinstance(data, list):
                    # The blob is a list of tool calls, e.g., [{"name": ..., "args": ...}]
                    tool_call_list = data
                elif isinstance(data, dict) and "name" in data and "args" in data:
                    # The blob is a single tool call object, e.g., {"name": ..., "args": ...}
                    tool_call_list = [data]
                else:
                    # Not a recognized format, skip this blob.
                    logger.debug(f"JSON blob is not in a recognized Gemini tool call format: {blob[:200]}")
                    continue

                for call_data in tool_call_list:
                    if not (isinstance(call_data, dict) and "name" in call_data and "args" in call_data):
                        logger.debug(f"Skipping malformed item in Gemini tool call list: {call_data}")
                        continue
                    
                    tool_name = call_data.get("name")
                    arguments = call_data.get("args")

                    if tool_name and isinstance(tool_name, str) and isinstance(arguments, dict):
                        # Pass id=None to trigger deterministic ID generation in ToolInvocation
                        tool_invocation = ToolInvocation(name=tool_name, arguments=arguments)
                        invocations.append(tool_invocation)
                        logger.info(f"Successfully parsed Gemini JSON tool invocation for '{tool_name}'.")
                    else:
                        logger.debug(f"Skipping malformed Gemini tool call data: {call_data}")

            except json.JSONDecodeError:
                logger.debug(f"Could not parse extracted text as JSON in {self.get_name()}. Blob: {blob[:200]}")
                # Not a tool call, ignore.
                continue
            except Exception as e:
                error_msg = f"Unexpected error while parsing JSON blob in {self.get_name()}: {e}. Blob: {blob[:200]}"
                logger.error(error_msg, exc_info=True)
                raise ToolUsageParseException(error_msg, original_exception=e)

        return invocations
