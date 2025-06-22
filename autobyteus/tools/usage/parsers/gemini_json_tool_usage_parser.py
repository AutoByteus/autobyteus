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
    Parses LLM responses for tool usage commands formatted in the Google Gemini style.
    It expects a JSON object with "name" and "args" keys.
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
            
            if isinstance(parsed_json, list):
                tool_calls = parsed_json
            elif isinstance(parsed_json, dict) and 'tool_calls' in parsed_json:
                 tool_calls = parsed_json['tool_calls']
            else:
                tool_calls = [parsed_json]

            for tool_data in tool_calls:
                tool_name = tool_data.get("name")
                arguments = tool_data.get("args")

                if tool_name and isinstance(tool_name, str) and isinstance(arguments, dict):
                    tool_invocation = ToolInvocation(name=tool_name, arguments=arguments, id=str(uuid.uuid4()))
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
        if (stripped_text.startswith('{') and stripped_text.endswith('}')) or \
           (stripped_text.startswith('[') and stripped_text.endswith(']')):
            return stripped_text
            
        return None
