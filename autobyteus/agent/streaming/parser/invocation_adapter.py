"""
ToolInvocation Adapter: Converts tool SegmentEvents into ToolInvocation objects.

This adapter serves as the bridge between the streaming parser (which emits SegmentEvents)
and the agent's tool execution system (which expects ToolInvocation objects).

Key Design: The segment_id from the parser becomes the invocationId, ensuring
consistent ID tracking from parse time through approval and execution.
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import logging

from .events import SegmentEvent, SegmentType, SegmentEventType
from .tool_syntax_registry import get_tool_syntax_spec
from .tool_call_parsing import parse_json_tool_call, parse_xml_arguments
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .json_parsing_strategies.base import JsonToolParsingStrategy


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
    
    def __init__(self, json_tool_parser: Optional["JsonToolParsingStrategy"] = None):
        # Track active tool segments: segment_id -> accumulated data
        self._active_segments: Dict[str, Dict[str, Any]] = {}
        self._json_tool_parser = json_tool_parser
    
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
        if event.segment_type != SegmentType.TOOL_CALL and get_tool_syntax_spec(event.segment_type) is None:
            return None
        
        # Initialize tracking for this tool segment
        metadata = event.payload.get("metadata", {})
        tool_name = metadata.get("tool_name")
        syntax_spec = get_tool_syntax_spec(event.segment_type)
        if syntax_spec:
            tool_name = syntax_spec.tool_name

        self._active_segments[event.segment_id] = {
            "segment_type": event.segment_type,
            "tool_name": tool_name,
            "content_buffer": "",
            "arguments": {},
            "syntax_spec": syntax_spec,
            "metadata": metadata,
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
        
        # Extract metadata from END event (display metadata only)
        metadata = event.payload.get("metadata", {})
        segment_type = segment_data.get("segment_type")
        tool_name = metadata.get("tool_name") or segment_data.get("tool_name")
        arguments: Dict[str, Any] = segment_data.get("arguments", {})
        content_buffer = segment_data.get("content_buffer", "")
        start_metadata = segment_data.get("metadata", {})
        syntax_spec = segment_data.get("syntax_spec")

        if syntax_spec:
            tool_name = syntax_spec.tool_name
            args = syntax_spec.build_arguments(
                {**start_metadata, **metadata},
                content_buffer,
            )
            if args is None:
                logger.warning(
                    f"Tool segment {event.segment_id} ended without required arguments for {tool_name}"
                )
                return None
            arguments = args
        elif segment_type == SegmentType.TOOL_CALL:
            content = content_buffer
            stripped = content.lstrip()
            parsed_call = None
            
            # Check if arguments were provided in start metadata (e.g. Sentinel parser)
            if start_metadata.get("arguments"):
                arguments = start_metadata["arguments"]
            elif stripped.startswith("{") or stripped.startswith("["):
                parsed_call = parse_json_tool_call(stripped, self._json_tool_parser)
            else:
                arguments = parse_xml_arguments(content)

            if parsed_call:
                tool_name = tool_name or parsed_call.get("name")
                arguments = parsed_call.get("arguments") or {}

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
