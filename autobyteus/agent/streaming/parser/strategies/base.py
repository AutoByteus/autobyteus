"""
Detection strategy interfaces for streaming parser.
"""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ..parser_context import ParserContext
    from ..states.base_state import BaseState


class DetectionStrategy(Protocol):
    """Protocol for detection strategies."""

    name: str

    def next_marker(self, context: "ParserContext", start_pos: int) -> int:
        """Return next marker index or -1 if not applicable."""
        ...

    def create_state(self, context: "ParserContext") -> "BaseState":
        """Create the state to handle parsing after this marker."""
        ...
