# file: autobyteus/autobyteus/tools/usage/parsers/gemini_json_tool_usage_parser.py
import json
import logging
import uuid
from typing import TYPE_CHECKING, List, Optional

from autobyteus.agent.tool_invocation import ToolInvocation
from .base_parser import BaseToolUsageParser

if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class GeminiJsonToolUsageParser(BaseToolUsageParser):
    """
    Parses LLM responses for a single tool usage command formatted in the Google Gemini style.
    It expects a single JSON object with "name" and "args" keys.
    """
    def get_name(self) -> str:
        return "gemini_json_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        invocations: List[ToolInvocation] = []
        response_text = self.extract_json_from_response(response.content)
        if not response_text:
            return invocations

        try:
            parsed_json = json.loads(response_text)

            if not isinstance(parsed_json, dict):
                logger.debug(f"Expected a JSON object for Gemini tool call, but got {type(parsed_json)}")
                return []

            # Gemini format is a single tool call object.
            tool_data = parsed_json
            tool_name = tool_data.get("name")
            arguments = tool_data.get("args")

            if tool_name and isinstance(tool_name, str) and isinstance(arguments, dict):
                # Pass id=None to trigger deterministic ID generation in ToolInvocation
                tool_invocation = ToolInvocation(name=tool_name, arguments=arguments)
                invocations.append(tool_invocation)
            else:
                logger.debug(f"Skipping malformed Gemini tool call data: {tool_data}")

            return invocations
        except json.JSONDecodeError:
            logger.debug(f"Failed to decode JSON for Gemini tool call: {response_text}")
            return []
        except Exception as e:
            logger.error(f"Error processing Gemini tool usage in {self.get_name()}: {e}", exc_info=True)
            return []
    
    def extract_json_from_response(self, text: str) -> Optional[str]:
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        stripped_text = text.strip()
        if stripped_text.startswith('{') and stripped_text.endswith('}'):
            return stripped_text
            
        return None
