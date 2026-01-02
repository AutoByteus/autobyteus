"""Gemini-style JSON tool-call parsing."""
from typing import Any, List
import json

from .base import ToolCallData, coerce_arguments


class GeminiJsonToolParsingStrategy:
    """Parses Gemini tool call JSON formats (name + args)."""

    def parse(self, raw_json: str) -> List[ToolCallData]:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return []

        calls: List[Any] = data if isinstance(data, list) else [data]
        parsed: List[ToolCallData] = []

        for call in calls:
            if not isinstance(call, dict):
                continue

            name = call.get("name")
            if not isinstance(name, str) or not name:
                continue

            arguments = coerce_arguments(call.get("args"))
            parsed.append({"name": name, "arguments": arguments})

        return parsed
