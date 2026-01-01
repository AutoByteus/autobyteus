"""
StreamingParser: Main driver class for the streaming response parser.

This is the primary entry point for parsing LLM responses in real-time.
It manages the state machine and provides a clean API for feeding chunks
and collecting parsed part events.
"""
from typing import List, Optional, Iterator, Union, Dict, Any
import logging

from .parser_context import ParserContext, ParserConfig
from .states.text_state import TextState
from .events import (
    PartEvent, PartStartEvent, PartDeltaEvent, PartEndEvent,
    MessagePart, TextPart, ToolCallPart, ReasoningPart
)

logger = logging.getLogger(__name__)


class StreamingParser:
    """
    Main driver for streaming LLM response parsing.
    
    This class provides a simple API for:
    1. Feeding chunks of text from an LLM stream
    2. Collecting structured PartEvents
    3. Finalizing the stream when complete
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize the streaming parser.
        
        Args:
            config: Optional parser configuration.
        """
        self._context = ParserContext(config)
        self._context.current_state = TextState(self._context)
        self._is_finalized = False
        logger.debug("StreamingParser initialized")

    @property
    def config(self) -> ParserConfig:
        """Get the parser configuration."""
        return self._context.config

    def feed(self, chunk: str) -> List[PartEvent]:
        """
        Feed a chunk of text from the LLM stream.
        
        This method:
        1. Appends the chunk to the internal buffer
        2. Runs the state machine until the buffer is exhausted
        3. Returns any events that were emitted
        
        Args:
            chunk: A string chunk from the LLM response stream.
            
        Returns:
            List of PartEvents emitted while processing this chunk.
            
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
        
        # Return all events emitted during processing
        return self._context.get_and_clear_events()

    def finalize(self) -> List[PartEvent]:
        """
        Signal that the LLM stream has ended.
        
        This method:
        1. Calls finalize() on the current state to flush any buffers
        2. Returns any final events
        3. Marks the parser as finalized
        
        Returns:
            List of any remaining PartEvents.
            
        Raises:
            RuntimeError: If called more than once.
        """
        if self._is_finalized:
            raise RuntimeError("finalize() has already been called")
        
        self._is_finalized = True
        
        # Finalize the current state
        self._context.current_state.finalize()
        
        # Return any remaining events
        return self._context.get_and_clear_events()

    def feed_and_finalize(self, text: str) -> List[PartEvent]:
        """
        Convenience method to parse a complete response in one call.
        
        Args:
            text: The complete LLM response text.
            
        Returns:
            All PartEvents from parsing the complete response.
        """
        events = self.feed(text)
        events.extend(self.finalize())
        return events

    @property
    def is_finalized(self) -> bool:
        """Check if the parser has been finalized."""
        return self._is_finalized

    def get_current_part_id(self) -> Optional[str]:
        """Get the ID of the currently active part, if any."""
        return self._context.get_current_part_id()

    def get_current_part_type(self) -> Optional[str]:
        """Get the type of the currently active part, if any."""
        return self._context.get_current_part_type()


def parse_complete_response(
    text: str, 
    config: Optional[ParserConfig] = None
) -> List[PartEvent]:
    """
    Convenience function to parse a complete LLM response.
    
    Args:
        text: The complete LLM response text.
        config: Optional parser configuration.
        
    Returns:
        List of all PartEvents from parsing.
    """
    parser = StreamingParser(config)
    return parser.feed_and_finalize(text)


def extract_segments(events: List[PartEvent]) -> List[MessagePart]:
    """
    Extract finalized segments (MessageParts) from a list of events.
    
    This is a utility function that converts the event stream into
    a list of typed MessagePart objects.
    
    Args:
        events: List of PartEvents.
        
    Returns:
        List of typed MessageParts (TextPart, ToolCallPart, etc).
    """
    segments: List[MessagePart] = []
    active_parts: Dict[str, Dict[str, Any]] = {}  # id -> {type, content, metadata}
    
    for event in events:
        if isinstance(event, PartStartEvent):
            active_parts[event.part_id] = {
                "type": event.part_type,
                "content": "",
                "metadata": event.metadata.copy()
            }
            
        elif isinstance(event, PartDeltaEvent):
            if event.part_id in active_parts:
                active_parts[event.part_id]["content"] += event.delta
                
        elif isinstance(event, PartEndEvent):
            if event.part_id in active_parts:
                data = active_parts.pop(event.part_id)
                
                # Merge final metadata (e.g. tool args might be accumulated or final)
                # But currently ToolParsingState updates metadata incrementally/at end 
                # and puts it in EndEvent? Yes, EndEvent has metadata copy.
                # So we update data['metadata'] with event.metadata
                data["metadata"].update(event.metadata)
                
                part_type = data["type"]
                content = data["content"]
                metadata = data["metadata"]
                
                if part_type == "text":
                    segments.append(TextPart(
                        id=event.part_id,
                        content=content
                    ))
                elif part_type == "tool_call":
                    segments.append(ToolCallPart(
                        id=event.part_id,
                        tool_name=metadata.get("tool_name", "unknown"),
                        arguments=metadata.get("arguments", {}),
                        raw_arguments=content 
                    ))
                elif part_type == "reasoning":
                    segments.append(ReasoningPart(
                        id=event.part_id,
                        content=content
                    ))
    
    # Handle unclosed segments (force close them)
    for part_id, data in active_parts.items():
        part_type = data["type"]
        content = data["content"]
        metadata = data["metadata"]
        
        if part_type == "text":
            segments.append(TextPart(id=part_id, content=content))
        elif part_type == "tool_call":
            segments.append(ToolCallPart(
                id=part_id, 
                tool_name=metadata.get("tool_name", "unknown"),
                arguments=metadata.get("arguments", {}),
                raw_arguments=content
            ))
        elif part_type == "reasoning":
            segments.append(ReasoningPart(id=part_id, content=content))
            
    return segments
