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
    A default parser for tool usage commands formatted as JSON.
    This serves as a fallback and attempts a best-effort parsing.
    """
    def get_name(self) -> str:
        return "default_json_tool_usage_parser"

    def parse(self, response: 'CompleteResponse') -> List[ToolInvocation]:
        invocations: List[ToolInvocation] = []
        response_text = self.extract_json_from_response(response.content)
        if not response_text:
            return invocations

        try:
            parsed_json = json.loads(response_text)
            tool_calls = []

            if isinstance(parsed_json, list):
                tool_calls = parsed_json
            elif isinstance(parsed_json, dict):
                if "tool_calls" in parsed_json and isinstance(parsed_json["tool_calls"], list):
                    tool_calls = parsed_json["tool_calls"]
                else:
                    tool_calls = [parsed_json]
            else:
                return invocations

            for tool_data in tool_calls:
                if not isinstance(tool_data, dict):
                    continue
                
                function_obj = tool_data.get("function") if isinstance(tool_data.get("function"), dict) else {}
                tool_name = tool_data.get("name") or function_obj.get("name")
                
                args = tool_data.get("arguments")
                if args is None: args = tool_data.get("args")
                if args is None: args = function_obj.get("arguments")
                
                if args is None:
                    logger.debug(f"Skipping tool call because 'arguments' or 'args' key is missing: {tool_data}")
                    continue

                if isinstance(args, str):
                    try:
                        arguments = json.loads(args)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse arguments string in default parser: {args}")
                        continue
                elif isinstance(args, dict):
                    arguments = args
                elif args is None:
                    arguments = {}
                else:
                    logger.warning(f"Unsupported type for arguments field: {type(args)}. Skipping tool call.")
                    continue

                tool_id = tool_data.get("id", str(uuid.uuid4()))

                if tool_name and isinstance(tool_name, str):
                    invocation = ToolInvocation(name=tool_name, arguments=arguments, id=tool_id)
                    invocations.append(invocation)

            return invocations

        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Default JSON parser failed to parse content: {e}")
            return []

    def extract_json_from_response(self, text: str) -> Optional[str]:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            return match.group(1).strip()
        
        stripped_text = text.strip()
        if (stripped_text.startswith('{') and stripped_text.endswith('}')) or \
           (stripped_text.startswith('[') and stripped_text.endswith(']')):
            try:
                json.loads(stripped_text)
                return stripped_text
            except json.JSONDecodeError:
                pass

        first_brace = text.find('{')
        first_bracket = text.find('[')
        start_index = -1

        if first_brace == -1 and first_bracket == -1: return None
        if first_brace != -1 and first_bracket != -1: start_index = min(first_brace, first_bracket)
        elif first_brace != -1: start_index = first_brace
        else: start_index = first_bracket
            
        json_substring = text[start_index:]
        try:
            json.loads(json_substring)
            return json_substring
        except json.JSONDecodeError:
            logger.debug(f"Found potential start of JSON, but substring was not valid: {json_substring[:100]}")
            
        return None
