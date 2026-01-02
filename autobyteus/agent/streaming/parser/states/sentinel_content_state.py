"""
SentinelContentState: Parses sentinel-delimited content blocks.
"""
from typing import TYPE_CHECKING, Dict

from .delimited_content_state import DelimitedContentState
from ..sentinel_format import END_MARKER
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class SentinelContentState(DelimitedContentState):
    """
    Parses content for a sentinel block until the matching end marker.
    """

    def __init__(
        self,
        context: "ParserContext",
        segment_type: SegmentType,
        metadata: Dict[str, object],
    ):
        self.SEGMENT_TYPE = segment_type
        self._metadata = metadata
        super().__init__(context, opening_tag="", closing_tag_override=END_MARKER)

    def _get_start_metadata(self) -> dict:
        return self._metadata
