# file: autobyteus/autobyteus/agent/streaming/agent_event_stream.py
import asyncio
import logging
import traceback
import functools 
import queue as standard_queue
from typing import AsyncIterator, Dict, Any, TYPE_CHECKING, List, Optional, Callable, Union

from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType 
from autobyteus.agent.streaming.stream_event_payloads import ( 
    create_assistant_chunk_data,
    create_assistant_complete_response_data,
    create_tool_interaction_log_entry_data,
    create_agent_operational_phase_transition_data, 
    create_error_event_data,
    create_tool_invocation_approval_requested_data,
    create_tool_invocation_auto_executing_data,
    AssistantChunkData,
    AssistantCompleteResponseData,
    ToolInteractionLogEntryData,
    AgentOperationalPhaseTransitionData,
    ToolInvocationApprovalRequestedData,
    ToolInvocationAutoExecutingData,
    ErrorEventData,
    EmptyData,
    StreamDataPayload,
)
from .queue_streamer import stream_queue_items 
from autobyteus.events.event_types import EventType 
from autobyteus.events.event_emitter import EventEmitter 

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier

logger = logging.getLogger(__name__)

_AES_INTERNAL_SENTINEL = object()

class AgentEventStream(EventEmitter): 
    def __init__(self, agent: 'Agent'):
        super().__init__() 
        
        from autobyteus.agent.agent import Agent as ConcreteAgent 
        if not isinstance(agent, ConcreteAgent):
            raise TypeError(f"AgentEventStream requires an Agent instance, got {type(agent).__name__}.")

        self.agent_id: str = agent.agent_id
        
        self._loop = asyncio.get_event_loop() 
        self._generic_stream_event_internal_q: standard_queue.Queue[Union[StreamEvent, object]] = standard_queue.Queue()

        self._notifier: Optional['AgentExternalEventNotifier'] = None
        if agent.context and agent.context.phase_manager: 
            self._notifier = agent.context.phase_manager.notifier
        
        if not self._notifier:
            logger.error(f"AgentEventStream for '{self.agent_id}': Notifier not available. No events will be streamed.")
            return

        self._register_listeners()
        
        logger.info(f"AgentEventStream (ID: {self.object_id}) initialized for agent_id '{self.agent_id}'. Subscribed to notifier.")

    def _register_listeners(self):
        """Subscribes this instance's handler to all relevant events from the notifier."""
        all_agent_event_types = [et for et in EventType if et.name.startswith("AGENT_")]
        
        for event_type in all_agent_event_types:
            self.subscribe_from(self._notifier, event_type, self._handle_notifier_event_sync)

    def _handle_notifier_event_sync(self, event_type: EventType, payload: Optional[Any] = None, object_id: Optional[str] = None, **kwargs):
        event_agent_id = kwargs.get("agent_id", self.agent_id) 
        
        typed_payload_for_stream_event: Optional[StreamDataPayload] = None
        stream_event_type_for_generic_stream: Optional[StreamEventType] = None

        try: 
            if event_type == EventType.AGENT_PHASE_IDLE_ENTERED:
                typed_payload_for_stream_event = create_agent_operational_phase_transition_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.AGENT_IDLE
            elif event_type.name.startswith("AGENT_PHASE_"):
                typed_payload_for_stream_event = create_agent_operational_phase_transition_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION
            elif event_type == EventType.AGENT_DATA_ASSISTANT_CHUNK:
                typed_payload_for_stream_event = create_assistant_chunk_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ASSISTANT_CHUNK
            elif event_type == EventType.AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE:
                typed_payload_for_stream_event = create_assistant_complete_response_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ASSISTANT_COMPLETE_RESPONSE
            elif event_type == EventType.AGENT_DATA_TOOL_LOG:
                typed_payload_for_stream_event = create_tool_interaction_log_entry_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_INTERACTION_LOG_ENTRY
            elif event_type == EventType.AGENT_REQUEST_TOOL_INVOCATION_APPROVAL:
                typed_payload_for_stream_event = create_tool_invocation_approval_requested_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED
            elif event_type == EventType.AGENT_TOOL_INVOCATION_AUTO_EXECUTING:
                typed_payload_for_stream_event = create_tool_invocation_auto_executing_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_INVOCATION_AUTO_EXECUTING
            elif event_type == EventType.AGENT_ERROR_OUTPUT_GENERATION:
                typed_payload_for_stream_event = create_error_event_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ERROR_EVENT
            
            elif event_type in [EventType.AGENT_DATA_ASSISTANT_CHUNK_STREAM_END, EventType.AGENT_DATA_TOOL_LOG_STREAM_END]:
                 pass 
            else:
                 logger.debug(f"AgentEventStream received internal event '{event_type.name}' with no direct stream mapping.")
        
        except Exception as e:
            logger.error(f"AgentEventStream error processing payload for event '{event_type.name}': {e}", exc_info=True)

        if typed_payload_for_stream_event and stream_event_type_for_generic_stream:
            stream_event = StreamEvent(
                agent_id=event_agent_id, 
                event_type=stream_event_type_for_generic_stream, 
                data=typed_payload_for_stream_event
            )
            self._generic_stream_event_internal_q.put(stream_event)

    async def close(self):
        logger.info(f"AgentEventStream (ID: {self.object_id}) for '{self.agent_id}': close() called. Unsubscribing all listeners and signaling.")
        self.unsubscribe_all_listeners()
        await self._loop.run_in_executor(None, self._generic_stream_event_internal_q.put, _AES_INTERNAL_SENTINEL)

    async def all_events(self) -> AsyncIterator[StreamEvent]:
        """The primary method to consume all structured events from the agent."""
        async for event in stream_queue_items(self._generic_stream_event_internal_q, _AES_INTERNAL_SENTINEL, f"agent_{self.agent_id}_all_events"):
            yield event

    # --- Convenience Stream Methods ---

    async def stream_assistant_chunks(self) -> AsyncIterator[AssistantChunkData]:
        """A convenience async generator that yields only assistant content/reasoning chunks."""
        async for event in self.all_events():
            if event.event_type == StreamEventType.ASSISTANT_CHUNK and isinstance(event.data, AssistantChunkData):
                yield event.data

    async def stream_assistant_final_response(self) -> AsyncIterator[AssistantCompleteResponseData]:
        """A convenience async generator that yields only the final, complete assistant responses."""
        async for event in self.all_events():
            if event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE and isinstance(event.data, AssistantCompleteResponseData):
                yield event.data

    async def stream_tool_logs(self) -> AsyncIterator[ToolInteractionLogEntryData]:
        """A convenience async generator that yields only tool interaction log entries."""
        async for event in self.all_events():
            if event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY and isinstance(event.data, ToolInteractionLogEntryData):
                yield event.data
    
    async def stream_phase_transitions(self) -> AsyncIterator[AgentOperationalPhaseTransitionData]:
        """A convenience async generator that yields only agent phase transition data."""
        async for event in self.all_events():
            if event.event_type == StreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION and isinstance(event.data, AgentOperationalPhaseTransitionData):
                yield event.data

    async def stream_tool_approval_requests(self) -> AsyncIterator[ToolInvocationApprovalRequestedData]:
        """A convenience async generator that yields only requests for tool invocation approval."""
        async for event in self.all_events():
            if event.event_type == StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED and isinstance(event.data, ToolInvocationApprovalRequestedData):
                yield event.data

    async def stream_tool_auto_executing(self) -> AsyncIterator[ToolInvocationAutoExecutingData]:
        """A convenience async generator that yields only events for tools being auto-executed."""
        async for event in self.all_events():
            if event.event_type == StreamEventType.TOOL_INVOCATION_AUTO_EXECUTING and isinstance(event.data, ToolInvocationAutoExecutingData):
                yield event.data

    async def stream_errors(self) -> AsyncIterator[ErrorEventData]:
        """A convenience async generator that yields only error events."""
        async for event in self.all_events():
            if event.event_type == StreamEventType.ERROR_EVENT and isinstance(event.data, ErrorEventData):
                yield event.data
