"""
ToolInvocation Adapter: Converts tool PartEvents into ToolInvocation objects.

This adapter serves as the bridge between the streaming parser (which emits PartEvents)
and the agent's tool execution system (which expects ToolInvocation objects).

Key Design: The part_id from the parser becomes the invocationId, ensuring
consistent ID tracking from parse time through approval and execution.
"""
from typing import Optional, List, Dict, Any, Union
import logging

from .events import PartEvent, PartStartEvent, PartDeltaEvent, PartEndEvent
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)


class ToolInvocationAdapter:
    """
    Converts tool call PartEvents into ToolInvocation objects.
    
    Usage:
        adapter = ToolInvocationAdapter()
        
        for event in parser.feed(chunk):
            result = adapter.process_event(event)
            if result:
                # Got a complete ToolInvocation
                enqueue_tool_invocation(result)
    """
    
    def __init__(self):
        # Track active tool parts: part_id -> accumulated data
        self._active_parts: Dict[str, Dict[str, Any]] = {}
    
    def process_event(self, event: PartEvent) -> Optional[ToolInvocation]:
        """
        Process a PartEvent and return a ToolInvocation if complete.
        
        Args:
            event: A PartEvent from the streaming parser.
            
        Returns:
            ToolInvocation if a tool part just completed, None otherwise.
        """
        if isinstance(event, PartStartEvent):
            return self._handle_start(event)
        elif isinstance(event, PartDeltaEvent):
            return self._handle_delta(event)
        elif isinstance(event, PartEndEvent):
            return self._handle_end(event)
        return None
    
    def _handle_start(self, event: PartStartEvent) -> None:
        """Handle PartStartEvent."""
        if event.part_type != "tool_call":
            return None
        
        # Initialize tracking for this tool part
        self._active_parts[event.part_id] = {
            "tool_name": event.metadata.get("tool_name"),
            "content_buffer": "",
            "arguments": {}
        }
        
        logger.debug(f"ToolInvocationAdapter: Started tracking part {event.part_id}")
        return None
    
    def _handle_delta(self, event: PartDeltaEvent) -> None:
        """Handle PartDeltaEvent."""
        if event.part_id not in self._active_parts:
            return None
        
        # Accumulate content (for display purposes or raw argument reconstruction)
        self._active_parts[event.part_id]["content_buffer"] += event.delta
        return None
    
    def _handle_end(self, event: PartEndEvent) -> Optional[ToolInvocation]:
        """
        Handle PartEndEvent.
        
        When a tool part ends, create and return a ToolInvocation.
        """
        if event.part_id not in self._active_parts:
            return None
        
        part_data = self._active_parts.pop(event.part_id)
        
        # Extract metadata from END event (parser puts parsed data here)
        metadata = event.metadata
        tool_name = metadata.get("tool_name") or part_data.get("tool_name")
        arguments = metadata.get("arguments") or part_data.get("arguments", {})
        
        if not tool_name:
            logger.warning(f"Tool part {event.part_id} ended without tool_name")
            return None
        
        # Create ToolInvocation with part_id as the invocation id
        invocation = ToolInvocation(
            name=tool_name,
            arguments=arguments,
            id=event.part_id  # Key: part_id becomes invocationId
        )
        
        logger.info(f"ToolInvocationAdapter: Created invocation {invocation.id} for tool {tool_name}")
        return invocation
    
    def process_events(self, events: List[PartEvent]) -> List[ToolInvocation]:
        """
        Process multiple events and return all completed ToolInvocations.
        
        Args:
            events: List of PartEvents from the parser.
            
        Returns:
            List of ToolInvocations for any completed tool parts.
        """
        invocations = []
        for event in events:
            result = self.process_event(event)
            if result:
                invocations.append(result)
        return invocations
    
    def reset(self) -> None:
        """Clear all tracking state."""
        self._active_parts.clear()
    
    def get_active_part_ids(self) -> List[str]:
        """Get IDs of currently tracked tool parts."""
        return list(self._active_parts.keys())

