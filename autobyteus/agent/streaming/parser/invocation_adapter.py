"""
ToolInvocation Adapter: Converts tool SegmentEvents into ToolInvocation objects.

This adapter serves as the bridge between the streaming parser (which emits SegmentEvents)
and the agent's tool execution system (which expects ToolInvocation objects).

Key Design: The segment_id from the parser becomes the invocationId, ensuring
consistent ID tracking from parse time through approval and execution.
"""
from typing import Optional, List, Dict, Any
import logging

from .events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)


class ToolInvocationAdapter:
    """
    Converts tool call SegmentEvents into ToolInvocation objects.
    
    Usage:
        adapter = ToolInvocationAdapter()
        
        for event in parser.feed(chunk):
            result = adapter.process_event(event)
            if result:
                # Got a complete ToolInvocation
                enqueue_tool_invocation(result)
    """
    
    def __init__(self):
        # Track active tool segments: segment_id -> accumulated data
        self._active_segments: Dict[str, Dict[str, Any]] = {}
    
    def process_event(self, event: SegmentEvent) -> Optional[ToolInvocation]:
        """
        Process a SegmentEvent and return a ToolInvocation if complete.
        
        Args:
            event: A SegmentEvent from the streaming parser.
            
        Returns:
            ToolInvocation if a tool segment just completed, None otherwise.
        """
        if event.event_type == SegmentEventType.START:
            return self._handle_start(event)
        elif event.event_type == SegmentEventType.CONTENT:
            return self._handle_content(event)
        elif event.event_type == SegmentEventType.END:
            return self._handle_end(event)
        return None
    
    def _handle_start(self, event: SegmentEvent) -> None:
        """Handle SEGMENT_START events."""
        if event.segment_type != SegmentType.TOOL_CALL:
            return None
        
        # Initialize tracking for this tool segment
        metadata = event.payload.get("metadata", {})
        self._active_segments[event.segment_id] = {
            "tool_name": metadata.get("tool_name"),
            "content_buffer": "",
            "arguments": {}
        }
        
        logger.debug(f"ToolInvocationAdapter: Started tracking segment {event.segment_id}")
        return None
    
    def _handle_content(self, event: SegmentEvent) -> None:
        """Handle SEGMENT_CONTENT events."""
        if event.segment_id not in self._active_segments:
            return None
        
        # Accumulate content (for display purposes)
        delta = event.payload.get("delta", "")
        self._active_segments[event.segment_id]["content_buffer"] += delta
        return None
    
    def _handle_end(self, event: SegmentEvent) -> Optional[ToolInvocation]:
        """
        Handle SEGMENT_END events.
        
        When a tool segment ends, create and return a ToolInvocation.
        """
        if event.segment_id not in self._active_segments:
            return None
        
        segment_data = self._active_segments.pop(event.segment_id)
        
        # Extract metadata from END event (parser puts parsed data here)
        metadata = event.payload.get("metadata", {})
        tool_name = metadata.get("tool_name") or segment_data.get("tool_name")
        arguments = metadata.get("arguments") or segment_data.get("arguments", {})
        
        if not tool_name:
            logger.warning(f"Tool segment {event.segment_id} ended without tool_name")
            return None
        
        # Create ToolInvocation with segment_id as the invocation id
        invocation = ToolInvocation(
            name=tool_name,
            arguments=arguments,
            id=event.segment_id  # Key: segment_id becomes invocationId
        )
        
        logger.info(f"ToolInvocationAdapter: Created invocation {invocation.id} for tool {tool_name}")
        return invocation
    
    def process_events(self, events: List[SegmentEvent]) -> List[ToolInvocation]:
        """
        Process multiple events and return all completed ToolInvocations.
        
        Args:
            events: List of SegmentEvents from the parser.
            
        Returns:
            List of ToolInvocations for any completed tool segments.
        """
        invocations = []
        for event in events:
            result = self.process_event(event)
            if result:
                invocations.append(result)
        return invocations
    
    def reset(self) -> None:
        """Clear all tracking state."""
        self._active_segments.clear()
    
    def get_active_segment_ids(self) -> List[str]:
        """Get IDs of currently tracked tool segments."""
        return list(self._active_segments.keys())
