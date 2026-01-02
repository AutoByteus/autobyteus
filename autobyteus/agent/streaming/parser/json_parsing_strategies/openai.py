"""OpenAI-style JSON tool-call parsing."""
from typing import Any, Dict, List
import json

from .base import ToolCallData, coerce_arguments


class OpenAiJsonToolParsingStrategy:
    """Parses OpenAI-compatible tool call JSON formats."""

    def parse(self, raw_json: str) -> List[ToolCallData]:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return []

        tool_calls = self._extract_tool_calls(data)
        parsed: List[ToolCallData] = []

        for call in tool_calls:
            if not isinstance(call, dict):
                continue

            # Unwrap if nested under "tool"
            if isinstance(call.get("tool"), dict):
                call = call.get("tool")
                if not isinstance(call, dict):
                    continue

            function_data: Dict[str, Any] = {}
            function_value = call.get("function")
            if isinstance(function_value, dict):
                function_data = function_value
            elif isinstance(function_value, str):
                # Default JSON format uses function as a string tool name.
                function_data = call
            elif "name" in call or "arguments" in call or "parameters" in call:
                function_data = call

            name = function_data.get("name") or function_data.get("function")
            if not isinstance(name, str) or not name:
                continue

            args = function_data.get("arguments")
            if args is None:
                args = function_data.get("parameters")
            arguments = coerce_arguments(args)

            parsed.append({"name": name, "arguments": arguments})

        return parsed

    def _extract_tool_calls(self, data: Any) -> List[Any]:
        if isinstance(data, dict):
            if isinstance(data.get("tool_calls"), list):
                return data.get("tool_calls")
            if isinstance(data.get("tools"), list):
                return data.get("tools")
            if isinstance(data.get("tool"), dict):
                return [data.get("tool")]
            return [data]
        if isinstance(data, list):
            return data
        return []
