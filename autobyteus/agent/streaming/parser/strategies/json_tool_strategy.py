"""
Detection strategy for JSON tool calls.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parser_context import ParserContext
    from ..states.base_state import BaseState


class JsonToolStrategy:
    name = "json_tool"

    def next_marker(self, context: "ParserContext", start_pos: int) -> int:
        if not context.parse_tool_calls:
            return -1
        next_curly = context.find("{", start_pos)
        next_bracket = context.find("[", start_pos)
        candidates = [idx for idx in (next_curly, next_bracket) if idx != -1]
        return min(candidates) if candidates else -1

    def create_state(self, context: "ParserContext") -> "BaseState":
        from ..states.json_initialization_state import JsonInitializationState
        return JsonInitializationState(context)
