"""
ParsingStreamingResponseHandler: Concrete implementation of StreamingResponseHandler that uses a parser.
"""
from typing import Optional, List, Callable, Any
import logging

from .streaming_response_handler import StreamingResponseHandler
from .parser.parser_factory import create_streaming_parser, resolve_parser_name
from .parser.events import SegmentEvent
from .parser.invocation_adapter import ToolInvocationAdapter
from .parser.parser_context import ParserConfig
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)


class ParsingStreamingResponseHandler(StreamingResponseHandler):
    """
    Handler that uses a StreamingParser to process the LLM response.
    """
    
    def __init__(
        self,
        on_segment_event: Optional[Callable[[SegmentEvent], None]] = None,
        on_tool_invocation: Optional[Callable[[ToolInvocation], None]] = None,
        config: Optional[ParserConfig] = None,
        parser_name: Optional[str] = None,
    ):
        """
        Initialize the parsing response handler.
        """
        self._parser_name = resolve_parser_name(parser_name)
        self._parser_config = config
        self._parser = create_streaming_parser(
            config=config,
            parser_name=self._parser_name,
        )
        self._adapter = ToolInvocationAdapter(
            json_tool_parser=self._parser.config.json_tool_parser
        )
        self._on_segment_event = on_segment_event
        self._on_tool_invocation = on_tool_invocation
        self._is_finalized = False
        
        # Accumulated data
        self._all_events: List[SegmentEvent] = []
        self._all_invocations: List[ToolInvocation] = []

    def feed(self, chunk: str) -> List[SegmentEvent]:
        if self._is_finalized:
            raise RuntimeError("Handler has been finalized, cannot feed more chunks.")
        
        if not chunk:
            return []
        
        events = self._parser.feed(chunk)
        self._process_events(events)
        return events

    def finalize(self) -> List[SegmentEvent]:
        if self._is_finalized:
            return []
        
        self._is_finalized = True
        events = self._parser.finalize()
        self._process_events(events)
        return events

    def _process_events(self, events: List[SegmentEvent]) -> None:
        for event in events:
            self._all_events.append(event)
            
            if self._on_segment_event:
                try:
                    self._on_segment_event(event)
                except Exception as e:
                    logger.error(f"Error in on_segment_event callback: {e}")
            
            invocation = self._adapter.process_event(event)
            if invocation:
                self._all_invocations.append(invocation)
                if self._on_tool_invocation:
                    try:
                        self._on_tool_invocation(invocation)
                    except Exception as e:
                        logger.error(f"Error in on_tool_invocation callback: {e}")

    def get_all_events(self) -> List[SegmentEvent]:
        return self._all_events.copy()

    def get_all_invocations(self) -> List[ToolInvocation]:
        return self._all_invocations.copy()

    def reset(self) -> None:
        self._parser = create_streaming_parser(
            config=self._parser_config,
            parser_name=self._parser_name,
        )
        self._adapter = ToolInvocationAdapter(
            json_tool_parser=self._parser.config.json_tool_parser
        )
        self._all_events.clear()
        self._all_invocations.clear()
        self._is_finalized = False
