"""
Shared types and helpers for JSON tool-call parsing strategies.
"""
from typing import Protocol, List, Dict, Any, TypedDict
import json


class ToolCallData(TypedDict):
    name: str
    arguments: Dict[str, Any]


class JsonToolParsingStrategy(Protocol):
    """Interface for provider-aware JSON tool parsing."""

    def parse(self, raw_json: str) -> List[ToolCallData]:
        """Parse JSON string into zero or more tool calls."""
        ...


def coerce_arguments(value: Any) -> Dict[str, Any]:
    """Normalize argument payload into a dict when possible."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}
