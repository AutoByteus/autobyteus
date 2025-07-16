# file: autobyteus/autobyteus/tools/usage/parsers/default_json_tool_usage_parser.py
import json
import logging
from typing import Dict, Any, TYPE_CHECKING, List

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser
from .exceptions import ToolUsageParseException
from ._json_extractor import _find_json_blobs

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class DefaultJsonToolUsageParser(BaseToolUsageParser):
    """
    A default parser for tool usage commands formatted as custom JSON.
    It robustly extracts potential JSON blobs and expects a 'tool' object
    with 'function' and 'parameters' keys.
    """
    def get_name(self) -> str:
        return "default_json_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        response_text = response.content
        json_blobs = _find_json_blobs(response_text)
        if not json_blobs:
            return []

        invocations: List[ToolInvocation] = []
        for blob in json_blobs:
            try:
                data = json.loads(blob)
                
                # This parser specifically looks for the {"tool": {...}} structure.
                if isinstance(data, dict) and "tool" in data:
                    tool_block = data.get("tool")
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
                    
                    try:
                        # Pass id=None to trigger deterministic ID generation.
                        tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=None)
                        invocations.append(tool_invocation)
                        logger.info(f"Successfully parsed default JSON tool invocation for '{tool_name}'.")
                    except Exception as e:
                        logger.error(f"Unexpected error creating ToolInvocation for tool '{tool_name}': {e}", exc_info=True)

            except json.JSONDecodeError:
                logger.debug(f"Could not parse extracted text as JSON in {self.get_name()}. Blob: {blob[:200]}")
                # This is likely not a tool call, so we can ignore it.
                continue
            except Exception as e:
                # If we're here, it's likely a valid JSON but with unexpected structure.
                # It's safer to raise this for upstream handling.
                error_msg = f"Unexpected error while parsing JSON blob in {self.get_name()}: {e}. Blob: {blob[:200]}"
                logger.error(error_msg, exc_info=True)
                raise ToolUsageParseException(error_msg, original_exception=e)
        
        return invocations
