"""
Detection strategy for sentinel-formatted segments.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..sentinel_format import START_MARKER

if TYPE_CHECKING:
    from ..parser_context import ParserContext
    from ..states.base_state import BaseState


class SentinelStrategy:
    name = "sentinel"

    def next_marker(self, context: "ParserContext", start_pos: int) -> int:
        return context.find(START_MARKER, start_pos)

    def create_state(self, context: "ParserContext") -> "BaseState":
        from ..states.sentinel_initialization_state import SentinelInitializationState
        return SentinelInitializationState(context)
