"""
Detection strategy for XML-like tags such as <file>, <bash>, <tool>, <!doctype>.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parser_context import ParserContext
    from ..states.base_state import BaseState


class XmlTagStrategy:
    name = "xml_tag"

    def next_marker(self, context: "ParserContext", start_pos: int) -> int:
        return context.find("<", start_pos)

    def create_state(self, context: "ParserContext") -> "BaseState":
        from ..states.xml_tag_initialization_state import XmlTagInitializationState
        return XmlTagInitializationState(context)
