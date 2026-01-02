"""
StreamingParser: Main driver class for the streaming response parser.

This is the primary entry point for parsing LLM responses in real-time.
It manages the state machine and provides a clean API for feeding chunks
and collecting parsed segment events.
"""
from typing import List, Optional, Iterator
import logging

from .parser_context import ParserContext, ParserConfig
from .states.text_state import TextState
from .events import SegmentEvent, SegmentType, SegmentEventType

logger = logging.getLogger(__name__)


class StreamingParser:
    """
    Main driver for streaming LLM response parsing.
    
    This class provides a simple API for:
    1. Feeding chunks of text from an LLM stream
    2. Collecting structured SegmentEvents
    3. Finalizing the stream when complete
    
    Example usage:
        parser = StreamingParser()
        
        # As chunks arrive from LLM
        for chunk in llm_stream:
            events = parser.feed(chunk)
            for event in events:
                # Send to WebSocket, update UI, etc.
                handle_event(event)
        
        # When stream ends
        final_events = parser.finalize()
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize the streaming parser.
        
        Args:
            config: Optional parser configuration. Defaults to parsing
                   XML tool calls.
        """
        self._context = ParserContext(config)
        self._context.current_state = TextState(self._context)
        self._is_finalized = False
        logger.debug("StreamingParser initialized")

    @property
    def config(self) -> ParserConfig:
        """Get the parser configuration."""
        return self._context.config

    def feed(self, chunk: str) -> List[SegmentEvent]:
        """
        Feed a chunk of text from the LLM stream.
        
        This method:
        1. Appends the chunk to the internal buffer
        2. Runs the state machine until the buffer is exhausted
        3. Returns any events that were emitted
        
        Args:
            chunk: A string chunk from the LLM response stream.
            
        Returns:
            List of SegmentEvents emitted while processing this chunk.
            
        Raises:
            RuntimeError: If called after finalize().
        """
        if self._is_finalized:
            raise RuntimeError("Cannot feed chunks after finalize() has been called")
        
        if not chunk:
            return []
        
        self._context.append(chunk)
        
        # Run the state machine until buffer is exhausted
        while self._context.has_more_chars():
            self._context.current_state.run()

        # Drop consumed buffer data to avoid unbounded growth
        self._context.compact()

        # Return all events emitted during processing
        return self._context.get_and_clear_events()

    def finalize(self) -> List[SegmentEvent]:
        """
        Signal that the LLM stream has ended.
        
        This method:
        1. Calls finalize() on the current state to flush any buffers
        2. Returns any final events
        3. Marks the parser as finalized
        
        Returns:
            List of any remaining SegmentEvents.
            
        Raises:
            RuntimeError: If called more than once.
        """
        if self._is_finalized:
            raise RuntimeError("finalize() has already been called")
        
        self._is_finalized = True
        
        # Finalize the current state
        self._context.current_state.finalize()

        # Clear any remaining buffer data
        self._context.compact()

        # Return any remaining events
        return self._context.get_and_clear_events()

    def feed_and_finalize(self, text: str) -> List[SegmentEvent]:
        """
        Convenience method to parse a complete response in one call.
        
        Args:
            text: The complete LLM response text.
            
        Returns:
            All SegmentEvents from parsing the complete response.
        """
        events = self.feed(text)
        events.extend(self.finalize())
        return events

    @property
    def is_finalized(self) -> bool:
        """Check if the parser has been finalized."""
        return self._is_finalized

    def get_current_segment_id(self) -> Optional[str]:
        """Get the ID of the currently active segment, if any."""
        return self._context.get_current_segment_id()

    def get_current_segment_type(self) -> Optional[SegmentType]:
        """Get the type of the currently active segment, if any."""
        return self._context.get_current_segment_type()


def parse_complete_response(
    text: str, 
    config: Optional[ParserConfig] = None
) -> List[SegmentEvent]:
    """
    Convenience function to parse a complete LLM response.
    
    Args:
        text: The complete LLM response text.
        config: Optional parser configuration.
        
    Returns:
        List of all SegmentEvents from parsing.
    """
    parser = StreamingParser(config)
    return parser.feed_and_finalize(text)


def extract_segments(events: List[SegmentEvent]) -> List[dict]:
    """
    Extract segment summaries from a list of events.
    
    This is a utility function that converts the event stream into
    a list of segment dictionaries with accumulated content.
    
    Args:
        events: List of SegmentEvents.
        
    Returns:
        List of segment dictionaries with 'id', 'type', 'content', 'metadata'.
    """
    segments = []
    current_segment = None
    
    for event in events:
        if event.event_type == SegmentEventType.START:
            current_segment = {
                "id": event.segment_id,
                "type": event.segment_type.value if event.segment_type else "unknown",
                "content": "",
                "metadata": event.payload.get("metadata", {})
            }
        elif event.event_type == SegmentEventType.CONTENT:
            if current_segment:
                delta = event.payload.get("delta", "")
                if isinstance(delta, str):
                    current_segment["content"] += delta
        elif event.event_type == SegmentEventType.END:
            if current_segment:
                segments.append(current_segment)
                current_segment = None
    
    # Handle unclosed segment
    if current_segment:
        segments.append(current_segment)
    
    return segments
