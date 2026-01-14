# file: autobyteus/autobyteus/agent/streaming/api_tool_call_streaming_response_handler.py
"""
ApiToolCallStreamingResponseHandler: Handler for API-provided tool calls.

This handler processes SDK-provided tool calls from providers like OpenAI,
Anthropic, and Gemini. It emits SegmentEvents and uses an internal
ToolInvocationAdapter to create ToolInvocations.
"""
import json
import uuid
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable

from .streaming_response_handler import StreamingResponseHandler
from ..segments.segment_events import SegmentEvent, SegmentType, SegmentEventType
from ..adapters.invocation_adapter import ToolInvocationAdapter
from ..api_tool_call.file_content_streamer import WriteFileContentStreamer, PatchFileContentStreamer
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import ChunkResponse

logger = logging.getLogger(__name__)


@dataclass
class ToolCallState:
    """Tracks the state of an in-progress tool call."""
    segment_id: str
    name: str
    accumulated_args: str = ""
    segment_type: SegmentType = SegmentType.TOOL_CALL
    streamer: Optional[object] = None
    path: Optional[str] = None
    segment_started: bool = False
    pending_content: str = ""


class ApiToolCallStreamingResponseHandler(StreamingResponseHandler):
    """
    Handler for API-provided tool calls (OpenAI, Anthropic, Gemini native tool calling).

    Responsibilities:
    1. Emit TEXT segments for text content
    2. Emit TOOL_CALL segments for SDK-provided tool calls
    3. Use internal ToolInvocationAdapter to create ToolInvocations

    Key Design:
    - Handler emits SegmentEvents
    - Internal adapter processes events to create ToolInvocations
    - get_all_invocations() returns adapter results (consistent interface)
    """

    def __init__(
        self,
        on_segment_event: Optional[Callable[[SegmentEvent], None]] = None,
        on_tool_invocation: Optional[Callable[[ToolInvocation], None]] = None,
        segment_id_prefix: str = "",
    ):
        self._on_segment_event = on_segment_event
        self._on_tool_invocation = on_tool_invocation
        self._segment_id_prefix = segment_id_prefix

        # Internal adapter for creating invocations from events
        self._adapter = ToolInvocationAdapter()

        # State tracking
        self._text_segment_id: Optional[str] = None
        self._active_tools: Dict[int, ToolCallState] = {}  # index -> state
        self._all_events: List[SegmentEvent] = []
        self._all_invocations: List[ToolInvocation] = []
        self._is_finalized = False

    def _generate_id(self) -> str:
        return f"{self._segment_id_prefix}{uuid.uuid4().hex}"

    @staticmethod
    def _resolve_segment_type(tool_name: str):
        if tool_name == "write_file":
            return SegmentType.WRITE_FILE, WriteFileContentStreamer()
        if tool_name == "patch_file":
            return SegmentType.PATCH_FILE, PatchFileContentStreamer()
        return SegmentType.TOOL_CALL, None

    def _emit(self, event: SegmentEvent) -> None:
        """Emit event and process through internal adapter."""
        self._all_events.append(event)
        
        # Notify callback
        if self._on_segment_event:
            try:
                self._on_segment_event(event)
            except Exception as e:
                logger.error(f"Error in on_segment_event callback: {e}")

        # Process through internal adapter
        invocation = self._adapter.process_event(event)
        if invocation:
            self._all_invocations.append(invocation)
            if self._on_tool_invocation:
                try:
                    self._on_tool_invocation(invocation)
                except Exception as e:
                    logger.error(f"Error in on_tool_invocation callback: {e}")

    def feed(self, chunk: ChunkResponse) -> List[SegmentEvent]:
        if self._is_finalized:
            raise RuntimeError("Handler has been finalized.")

        events = []

        # 1. Handle text content → TEXT segment
        if chunk.content:
            if self._text_segment_id is None:
                self._text_segment_id = self._generate_id()
                start_event = SegmentEvent.start(
                    segment_id=self._text_segment_id,
                    segment_type=SegmentType.TEXT
                )
                self._emit(start_event)
                events.append(start_event)

            content_event = SegmentEvent.content(
                segment_id=self._text_segment_id,
                delta=chunk.content
            )
            self._emit(content_event)
            events.append(content_event)

        # 2. Handle tool calls from SDK
        if chunk.tool_calls:
            for delta in chunk.tool_calls:
                if delta.index not in self._active_tools:
                    # New tool call - emit SEGMENT_START
                    seg_id = delta.call_id or self._generate_id()
                    tool_name = delta.name or ""
                    segment_type, streamer = self._resolve_segment_type(tool_name)
                    self._active_tools[delta.index] = ToolCallState(
                        segment_id=seg_id,
                        name=tool_name,
                        accumulated_args="",
                        segment_type=segment_type,
                        streamer=streamer,
                    )
                    if segment_type == SegmentType.TOOL_CALL:
                        start_event = SegmentEvent.start(
                            segment_id=seg_id,
                            segment_type=segment_type,
                            tool_name=tool_name,
                        )
                        self._active_tools[delta.index].segment_started = True
                        self._emit(start_event)
                        events.append(start_event)

                # Accumulate arguments and emit content delta (for UI streaming)
                if delta.arguments_delta:
                    state = self._active_tools[delta.index]
                    state.accumulated_args += delta.arguments_delta

                    if state.segment_type == SegmentType.TOOL_CALL:
                        if not state.segment_started:
                            start_event = SegmentEvent.start(
                                segment_id=state.segment_id,
                                segment_type=state.segment_type,
                                tool_name=state.name,
                            )
                            state.segment_started = True
                            self._emit(start_event)
                            events.append(start_event)
                        content_event = SegmentEvent.content(
                            segment_id=state.segment_id,
                            delta=delta.arguments_delta,
                        )
                        self._emit(content_event)
                        events.append(content_event)
                    else:
                        update = state.streamer.feed(delta.arguments_delta) if state.streamer else None
                        if update and update.path and not state.path:
                            state.path = update.path
                        if not state.segment_started and state.path:
                            start_event = SegmentEvent.start(
                                segment_id=state.segment_id,
                                segment_type=state.segment_type,
                                tool_name=state.name,
                                path=state.path,
                            )
                            state.segment_started = True
                            self._emit(start_event)
                            events.append(start_event)
                            if state.pending_content:
                                content_event = SegmentEvent.content(
                                    segment_id=state.segment_id,
                                    delta=state.pending_content,
                                )
                                self._emit(content_event)
                                events.append(content_event)
                                state.pending_content = ""
                        if update and update.content_delta:
                            if state.segment_started:
                                content_event = SegmentEvent.content(
                                    segment_id=state.segment_id,
                                    delta=update.content_delta,
                                )
                                self._emit(content_event)
                                events.append(content_event)
                            else:
                                state.pending_content += update.content_delta

                # Update name if provided later
                if delta.name and not self._active_tools[delta.index].name:
                    self._active_tools[delta.index].name = delta.name

        return events

    def finalize(self) -> List[SegmentEvent]:
        if self._is_finalized:
            return []

        self._is_finalized = True
        events = []

        # Close text segment
        if self._text_segment_id:
            end_event = SegmentEvent.end(segment_id=self._text_segment_id)
            self._emit(end_event)
            events.append(end_event)

        # Close tool segments with pre-parsed arguments in metadata
        for state in self._active_tools.values():
            if state.segment_type in {SegmentType.WRITE_FILE, SegmentType.PATCH_FILE}:
                if not state.segment_started:
                    start_meta = {"tool_name": state.name}
                    if state.path:
                        start_meta["path"] = state.path
                    start_event = SegmentEvent.start(
                        segment_id=state.segment_id,
                        segment_type=state.segment_type,
                        **start_meta,
                    )
                    state.segment_started = True
                    self._emit(start_event)
                    events.append(start_event)
                    if state.pending_content:
                        content_event = SegmentEvent.content(
                            segment_id=state.segment_id,
                            delta=state.pending_content,
                        )
                        self._emit(content_event)
                        events.append(content_event)
                        state.pending_content = ""
            if state.segment_type == SegmentType.TOOL_CALL:
                # Parse accumulated JSON arguments
                try:
                    parsed_args = json.loads(state.accumulated_args) if state.accumulated_args else {}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments for {state.name}: {e}")
                    parsed_args = {}

                # Emit SEGMENT_END with arguments in metadata
                # The internal adapter will use this to create ToolInvocation
                end_event = SegmentEvent(
                    event_type=SegmentEventType.END,
                    segment_id=state.segment_id,
                    payload={
                        "metadata": {
                            "tool_name": state.name,
                            "arguments": parsed_args,  # Pre-parsed for adapter
                        }
                    }
                )
            else:
                metadata = {}
                if state.path:
                    metadata["path"] = state.path
                end_event = SegmentEvent(
                    event_type=SegmentEventType.END,
                    segment_id=state.segment_id,
                    payload={"metadata": metadata} if metadata else {},
                )
            self._emit(end_event)
            events.append(end_event)

        if self._all_invocations:
            logger.info(
                "ApiToolCallStreamingResponseHandler finalized %d tool invocations.",
                len(self._all_invocations),
            )

        return events

    def get_all_events(self) -> List[SegmentEvent]:
        return self._all_events.copy()

    def get_all_invocations(self) -> List[ToolInvocation]:
        """Returns invocations created by the internal adapter."""
        return self._all_invocations.copy()

    def reset(self) -> None:
        self._text_segment_id = None
        self._active_tools.clear()
        self._all_events.clear()
        self._all_invocations.clear()
        self._adapter = ToolInvocationAdapter()
        self._is_finalized = False
