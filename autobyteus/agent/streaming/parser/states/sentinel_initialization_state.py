"""
SentinelInitializationState: Parses sentinel start headers.
"""
import json
from typing import TYPE_CHECKING, Dict, Optional

from .base_state import BaseState
from ..events import SegmentType
from ..sentinel_format import START_MARKER, MARKER_END

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class SentinelInitializationState(BaseState):
    """
    Parses the sentinel start header and transitions to content state.
    """

    def __init__(self, context: "ParserContext"):
        super().__init__(context)
        self._header_buffer = ""

    def run(self) -> None:
        from .text_state import TextState
        from .sentinel_content_state import SentinelContentState

        if not self.context.has_more_chars():
            return

        start_pos = self.context.get_position()
        end_idx = self.context.find(MARKER_END, start_pos)

        if end_idx == -1:
            self._header_buffer += self.context.consume_remaining()
            if not self._is_possible_prefix(self._header_buffer):
                self.context.append_text_segment(self._header_buffer)
                self.context.transition_to(TextState(self.context))
            return

        self._header_buffer += self.context.consume(end_idx - start_pos + len(MARKER_END))

        if not self._header_buffer.startswith(START_MARKER):
            self.context.append_text_segment(self._header_buffer)
            self.context.transition_to(TextState(self.context))
            return

        header_json = self._header_buffer[len(START_MARKER):]
        if header_json.endswith(MARKER_END):
            header_json = header_json[:-len(MARKER_END)]
        header_json = header_json.strip()

        if not header_json:
            self.context.append_text_segment(self._header_buffer)
            self.context.transition_to(TextState(self.context))
            return

        data = self._parse_header_json(header_json)
        if not data:
            self.context.append_text_segment(self._header_buffer)
            self.context.transition_to(TextState(self.context))
            return

        type_str = data.get("type")
        segment_type = self._map_segment_type(type_str)

        if segment_type is None:
            self.context.append_text_segment(self._header_buffer)
            self.context.transition_to(TextState(self.context))
            return

        metadata = dict(data)
        metadata.pop("type", None)

        if self.context.get_current_segment_type() == SegmentType.TEXT:
            self.context.emit_segment_end()

        self.context.transition_to(
            SentinelContentState(
                self.context,
                segment_type=segment_type,
                metadata=metadata,
            )
        )

    def finalize(self) -> None:
        from .text_state import TextState

        if self.context.has_more_chars():
            self._header_buffer += self.context.consume_remaining()

        if self._header_buffer:
            self.context.append_text_segment(self._header_buffer)
        self.context.transition_to(TextState(self.context))

    def _is_possible_prefix(self, buffer: str) -> bool:
        return START_MARKER.startswith(buffer) or buffer.startswith(START_MARKER)

    def _parse_header_json(self, header_json: str) -> Optional[Dict[str, object]]:
        try:
            data = json.loads(header_json)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def _map_segment_type(self, type_str: Optional[str]) -> Optional[SegmentType]:
        if not type_str:
            return None
        value = type_str.strip().lower()
        mapping = {
            "text": SegmentType.TEXT,
            "tool": SegmentType.TOOL_CALL,
            "tool_call": SegmentType.TOOL_CALL,
            "write_file": SegmentType.WRITE_FILE,
            "run_bash": SegmentType.RUN_BASH,
        }
        return mapping.get(value)
