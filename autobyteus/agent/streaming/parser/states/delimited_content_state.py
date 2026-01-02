"""
DelimitedContentState: Base state for content blocks terminated by a closing tag.

Provides streaming-safe emission with a holdback tail to prevent partial
closing tags from being emitted.
"""
from typing import TYPE_CHECKING, Optional, Dict

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class DelimitedContentState(BaseState):
    """
    Base class for parsing delimited content blocks.

    Subclasses must define:
    - CLOSING_TAG: The closing tag string (e.g., "</file>")
    - SEGMENT_TYPE: SegmentType for emitted segments
    """

    CLOSING_TAG = ""
    SEGMENT_TYPE: Optional[SegmentType] = None

    def __init__(
        self,
        context: "ParserContext",
        opening_tag: str,
        closing_tag_override: Optional[str] = None,
    ):
        super().__init__(context)
        self._opening_tag = opening_tag
        self._segment_started = False
        self._tail = ""
        self._closing_tag = closing_tag_override if closing_tag_override is not None else self.CLOSING_TAG
        self._closing_tag_lower = self._closing_tag.lower()
        self._holdback_len = max(len(self._closing_tag) - 1, 0)

    def _can_start_segment(self) -> bool:
        """Return False to emit opening tag as text and abort."""
        return True

    def _get_start_metadata(self) -> Dict[str, str]:
        """Metadata to include on segment start."""
        return {}

    def _opening_content(self) -> Optional[str]:
        """Optional content to emit immediately after segment start."""
        return None

    def _on_segment_complete(self) -> None:
        """Hook invoked just before segment end is emitted."""
        return None

    def _should_emit_closing_tag(self) -> bool:
        """Whether to emit the closing tag as content."""
        return False

    def run(self) -> None:
        from .text_state import TextState

        if not self._segment_started:
            if not self._can_start_segment():
                self.context.append_text_segment(self._opening_tag)
                self.context.transition_to(TextState(self.context))
                return

            if self.SEGMENT_TYPE is None:
                raise RuntimeError("SEGMENT_TYPE is not defined for DelimitedContentState.")

            self.context.emit_segment_start(self.SEGMENT_TYPE, **self._get_start_metadata())
            self._segment_started = True

            opening_content = self._opening_content()
            if opening_content:
                self.context.emit_segment_content(opening_content)

        if not self.context.has_more_chars():
            return

        available = self.context.consume_remaining()
        combined = self._tail + available

        if combined:
            idx = combined.lower().find(self._closing_tag_lower)
        else:
            idx = -1

        if idx != -1:
            content_before = combined[:idx]
            if content_before:
                self.context.emit_segment_content(content_before)

            if self._should_emit_closing_tag() and self._closing_tag:
                self.context.emit_segment_content(self._closing_tag)

            tail_len = len(self._tail)
            closing_len = len(self._closing_tag)
            if idx < tail_len:
                consumed_from_available = idx + closing_len - tail_len
            else:
                consumed_from_available = (idx - tail_len) + closing_len

            extra = len(available) - consumed_from_available
            if extra > 0:
                self.context.rewind_by(extra)

            self._tail = ""
            self._on_segment_complete()
            self.context.emit_segment_end()
            self.context.transition_to(TextState(self.context))
            return

        if self._holdback_len == 0:
            if combined:
                self.context.emit_segment_content(combined)
            self._tail = ""
            return

        if len(combined) > self._holdback_len:
            safe = combined[:-self._holdback_len]
            if safe:
                self.context.emit_segment_content(safe)
            self._tail = combined[-self._holdback_len:]
        else:
            self._tail = combined

    def finalize(self) -> None:
        from .text_state import TextState

        remaining = self.context.consume_remaining() if self.context.has_more_chars() else ""

        if not self._segment_started:
            text = self._opening_tag + self._tail + remaining
            if text:
                self.context.append_text_segment(text)
        else:
            if self._tail or remaining:
                self.context.emit_segment_content(self._tail + remaining)
            self._tail = ""
            self.context.emit_segment_end()

        self.context.transition_to(TextState(self.context))
