"""
StreamingResponseHandler: Wraps StreamingParser for use during LLM response streaming.

This handler integrates the StreamingParser with the agent's event system, providing:
1. Chunk-by-chunk parsing of LLM responses
2. Emission of PartEvents
3. Automatic creation of ToolInvocations when tool parts complete

It serves as the bridge between the LLM response stream and the parsed part output.
"""
from typing import Optional, List, Callable, Any
import logging

from .parser.streaming_parser import StreamingParser
from .parser.events import PartEvent
from .parser.invocation_adapter import ToolInvocationAdapter
from .parser.parser_context import ParserConfig
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)


class StreamingResponseHandler:
    """
    High-level handler for streaming LLM response parsing.
    
    Combines StreamingParser + ToolInvocationAdapter to provide:
    - PartEvents for UI streaming
    - ToolInvocations for tool execution
    
    Usage:
        handler = StreamingResponseHandler(
            on_part_event=send_to_websocket,
            on_tool_invocation=enqueue_tool_event
        )
        
        async for chunk in llm.stream():
            handler.feed(chunk.content)
        
        handler.finalize()
    """
    
    def __init__(
        self,
        on_part_event: Optional[Callable[[PartEvent], None]] = None,
        on_tool_invocation: Optional[Callable[[ToolInvocation], None]] = None,
        config: Optional[ParserConfig] = None
    ):
        """
        Initialize the streaming response handler.
        
        Args:
            on_part_event: Callback for each PartEvent (for UI streaming).
            on_tool_invocation: Callback for completed ToolInvocations.
            config: Parser configuration.
        """
        self._parser = StreamingParser(config=config)
        self._adapter = ToolInvocationAdapter()
        self._on_part_event = on_part_event
        self._on_tool_invocation = on_tool_invocation
        self._is_finalized = False
        
        # Accumulated data
        self._all_events: List[PartEvent] = []
        self._all_invocations: List[ToolInvocation] = []

    def feed(self, chunk: str) -> List[PartEvent]:
        """
        Process a chunk of LLM response text.
        
        Args:
            chunk: Raw text chunk from LLM.
            
        Returns:
            List of PartEvents emitted during processing.
        """
        if self._is_finalized:
            raise RuntimeError("Handler has been finalized, cannot feed more chunks.")
        
        if not chunk:
            return []
        
        events = self._parser.feed(chunk)
        self._process_events(events)
        return events

    def finalize(self) -> List[PartEvent]:
        """
        Finalize parsing and emit any remaining parts.
        
        Returns:
            List of final PartEvents.
        """
        if self._is_finalized:
            return []
        
        self._is_finalized = True
        events = self._parser.finalize()
        self._process_events(events)
        return events

    def _process_events(self, events: List[PartEvent]) -> None:
        """Process events through callbacks and adapter."""
        for event in events:
            # Store for later retrieval
            self._all_events.append(event)
            
            # Notify via callback
            if self._on_part_event:
                try:
                    self._on_part_event(event)
                except Exception as e:
                    logger.error(f"Error in on_part_event callback: {e}")
            
            # Check for tool invocations
            invocation = self._adapter.process_event(event)
            if invocation:
                self._all_invocations.append(invocation)
                if self._on_tool_invocation:
                    try:
                        self._on_tool_invocation(invocation)
                    except Exception as e:
                        logger.error(f"Error in on_tool_invocation callback: {e}")

    def get_all_events(self) -> List[PartEvent]:
        """Get all PartEvents emitted so far."""
        return self._all_events.copy()

    def get_all_invocations(self) -> List[ToolInvocation]:
        """Get all ToolInvocations created so far."""
        return self._all_invocations.copy()

    def reset(self) -> None:
        """Reset the handler for reuse."""
        self._parser = StreamingParser(config=self._parser.config)
        self._adapter.reset()
        self._all_events.clear()
        self._all_invocations.clear()
        self._is_finalized = False
