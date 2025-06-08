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
    create_assistant_complete_response_data, # UPDATED import
    create_tool_interaction_log_entry_data,
    create_agent_operational_phase_transition_data, 
    create_error_event_data,
    create_tool_invocation_approval_requested_data,
    EmptyData,
    StreamDataPayload,
    ErrorEventData, 
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
    """
    Provides access to various output streams from an agent, unified into
    a single `all_events()` stream of `StreamEvent` objects.
    It subscribes to events from the agent's AgentExternalEventNotifier and uses
    standard `queue.Queue` instances for thread-safe communication between the
    synchronous event handler and asynchronous stream consumers.
    """

    def __init__(self, agent: 'Agent'): # pragma: no cover
        super().__init__() 
        
        from autobyteus.agent.agent import Agent as ConcreteAgent 
        if not isinstance(agent, ConcreteAgent):
            raise TypeError(f"AgentEventStream requires an Agent instance, got {type(agent).__name__}.")

        self.agent_id: str = agent.agent_id
        
        self._loop = asyncio.get_event_loop() 
        self._assistant_chunk_internal_q: standard_queue.Queue[Union[ChunkResponse, object]] = standard_queue.Queue()
        self._assistant_final_message_internal_q: standard_queue.Queue[Union[CompleteResponse, object]] = standard_queue.Queue()
        self._tool_log_internal_q: standard_queue.Queue[Union[str, object]] = standard_queue.Queue()
        self._tool_approval_internal_q: standard_queue.Queue[Union[Dict[str, Any], object]] = standard_queue.Queue()
        self._generic_stream_event_internal_q: standard_queue.Queue[Union[StreamEvent, object]] = standard_queue.Queue()

        self._notifier: Optional['AgentExternalEventNotifier'] = None
        if agent.context and agent.context.phase_manager: 
            self._notifier = agent.context.phase_manager.notifier
        
        if not self._notifier:
            logger.error(f"AgentEventStream for '{self.agent_id}': AgentExternalEventNotifier not available. No events will be streamed.")
        
        self._subscribed_notifier_event_types: List[EventType] = [
            EventType.AGENT_PHASE_UNINITIALIZED_ENTERED,
            EventType.AGENT_PHASE_INITIALIZING_TOOLS_STARTED,
            EventType.AGENT_PHASE_INITIALIZING_PROMPT_STARTED,
            EventType.AGENT_PHASE_INITIALIZING_LLM_STARTED,
            EventType.AGENT_PHASE_IDLE_ENTERED,
            EventType.AGENT_PHASE_PROCESSING_USER_INPUT_STARTED,
            EventType.AGENT_PHASE_AWAITING_LLM_RESPONSE_STARTED,
            EventType.AGENT_PHASE_ANALYZING_LLM_RESPONSE_STARTED,
            EventType.AGENT_PHASE_AWAITING_TOOL_APPROVAL_STARTED, 
            EventType.AGENT_PHASE_EXECUTING_TOOL_STARTED,
            EventType.AGENT_PHASE_PROCESSING_TOOL_RESULT_STARTED,
            EventType.AGENT_PHASE_SHUTTING_DOWN_STARTED,
            EventType.AGENT_PHASE_SHUTDOWN_COMPLETED,
            EventType.AGENT_PHASE_ERROR_ENTERED,
            EventType.AGENT_DATA_ASSISTANT_CHUNK,
            EventType.AGENT_DATA_ASSISTANT_CHUNK_STREAM_END,
            EventType.AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE,
            EventType.AGENT_DATA_TOOL_LOG,
            EventType.AGENT_DATA_TOOL_LOG_STREAM_END,
            EventType.AGENT_REQUEST_TOOL_INVOCATION_APPROVAL,
            EventType.AGENT_ERROR_OUTPUT_GENERATION,
        ]
        self._registered_event_handlers: Dict[EventType, Callable] = {}
        self._register_notifier_listeners()
        
        logger.info(f"AgentEventStream initialized for agent_id '{self.agent_id}'. Notifier listener status: {'Active' if self._notifier else 'Inactive'}.")

    def _register_notifier_listeners(self): # pragma: no cover
        if not self._notifier:
            return
        for event_type_to_sub in self._subscribed_notifier_event_types:
            handler_with_event_type = functools.partial(self._handle_notifier_event_sync, event_type=event_type_to_sub)
            self._registered_event_handlers[event_type_to_sub] = handler_with_event_type
            try:
                self.subscribe_from(self._notifier, event_type_to_sub, handler_with_event_type)
                logger.debug(f"AgentEventStream '{self.agent_id}': Subscribed to {event_type_to_sub.name} from notifier {self._notifier.object_id}.")
            except Exception as e: 
                logger.error(f"AgentEventStream '{self.agent_id}': Failed to subscribe to {event_type_to_sub.name}: {e}", exc_info=True)
    
    def _unregister_notifier_listeners(self): # pragma: no cover
        if not self._notifier or not self._registered_event_handlers:
            return
        for event_type_to_unsub, handler_to_unsub in self._registered_event_handlers.items():
            try:
                self.unsubscribe_from(self._notifier, event_type_to_unsub, handler_to_unsub)
                logger.debug(f"AgentEventStream '{self.agent_id}': Unsubscribed from {event_type_to_unsub.name} from notifier {self._notifier.object_id}.")
            except Exception as e: 
                logger.warning(f"AgentEventStream '{self.agent_id}': Failed to unsubscribe from {event_type_to_unsub.name} (may be harmless): {e}")
        self._registered_event_handlers.clear()

    def _handle_notifier_event_sync(self, *args, event_type: EventType, object_id: Optional[str] = None, **received_kwargs: Any): 
        event_agent_id = received_kwargs.get("agent_id", self.agent_id) 
        actual_payload_content = received_kwargs.get("payload")

        logger.debug(f"AgentEventStream '{self.agent_id}': Sync handler received notifier event. Type='{event_type.name}', EmitterID='{object_id}', AgentID='{event_agent_id}', Payload type='{type(actual_payload_content).__name__}'")
        
        typed_payload_for_stream_event: Optional[StreamDataPayload] = None
        stream_event_type_for_generic_stream: Optional[StreamEventType] = None

        try: 
            if event_type == EventType.AGENT_PHASE_IDLE_ENTERED:
                typed_payload_for_stream_event = create_agent_operational_phase_transition_data(actual_payload_content)
                stream_event_type_for_generic_stream = StreamEventType.AGENT_IDLE
            
            elif event_type.name.startswith("AGENT_PHASE_"): 
                typed_payload_for_stream_event = create_agent_operational_phase_transition_data(actual_payload_content) 
                stream_event_type_for_generic_stream = StreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION
            
            elif event_type == EventType.AGENT_DATA_ASSISTANT_CHUNK: 
                if isinstance(actual_payload_content, ChunkResponse):
                    self._assistant_chunk_internal_q.put(actual_payload_content)
                    typed_payload_for_stream_event = create_assistant_chunk_data(actual_payload_content)
                    stream_event_type_for_generic_stream = StreamEventType.ASSISTANT_CHUNK
                else: 
                    logger.warning(f"AgentEventStream '{self.agent_id}': Expected ChunkResponse for AGENT_DATA_ASSISTANT_CHUNK, got {type(actual_payload_content)}.")

            elif event_type == EventType.AGENT_DATA_ASSISTANT_CHUNK_STREAM_END: 
                self._assistant_chunk_internal_q.put(_AES_INTERNAL_SENTINEL)

            elif event_type == EventType.AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE:
                if isinstance(actual_payload_content, CompleteResponse):
                    self._assistant_final_message_internal_q.put(actual_payload_content)
                    self._assistant_final_message_internal_q.put(_AES_INTERNAL_SENTINEL) 
                    typed_payload_for_stream_event = create_assistant_complete_response_data(actual_payload_content)
                    stream_event_type_for_generic_stream = StreamEventType.ASSISTANT_COMPLETE_RESPONSE
                else: 
                     logger.warning(f"AgentEventStream '{self.agent_id}': Expected CompleteResponse for AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE, got {type(actual_payload_content)}.")

            elif event_type == EventType.AGENT_DATA_TOOL_LOG: 
                typed_payload_for_stream_event = create_tool_interaction_log_entry_data(actual_payload_content)
                if isinstance(actual_payload_content, str): 
                    self._tool_log_internal_q.put(actual_payload_content)
                elif isinstance(actual_payload_content, dict) and 'log_entry' in actual_payload_content: 
                    self._tool_log_internal_q.put(actual_payload_content['log_entry'])
                stream_event_type_for_generic_stream = StreamEventType.TOOL_INTERACTION_LOG_ENTRY
                
            elif event_type == EventType.AGENT_DATA_TOOL_LOG_STREAM_END: 
                self._tool_log_internal_q.put(_AES_INTERNAL_SENTINEL)

            elif event_type == EventType.AGENT_REQUEST_TOOL_INVOCATION_APPROVAL: 
                if isinstance(actual_payload_content, dict):
                    self._tool_approval_internal_q.put(actual_payload_content)
                    self._tool_approval_internal_q.put(_AES_INTERNAL_SENTINEL) 
                    typed_payload_for_stream_event = create_tool_invocation_approval_requested_data(actual_payload_content)
                    stream_event_type_for_generic_stream = StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED
                else: 
                    logger.warning(f"AgentEventStream '{self.agent_id}': Expected dict for AGENT_REQUEST_TOOL_INVOCATION_APPROVAL, got {type(actual_payload_content)}.")
            
            elif event_type == EventType.AGENT_ERROR_OUTPUT_GENERATION: 
                typed_payload_for_stream_event = create_error_event_data(actual_payload_content)
                stream_event_type_for_generic_stream = StreamEventType.ERROR_EVENT
            
            else: 
                logger.warning(f"AgentEventStream '{self.agent_id}': Sync handler received subscribed event type '{event_type.name}' with no specific data mapping logic. Payload content type: {type(actual_payload_content).__name__}")
                if actual_payload_content is None or (isinstance(actual_payload_content, dict) and not actual_payload_content) :
                    typed_payload_for_stream_event = EmptyData()
                
        except ValueError as ve: 
            logger.error(f"AgentEventStream '{self.agent_id}': Error creating typed payload for event {event_type.name}: {ve}. Payload was: {actual_payload_content!r}")
            typed_payload_for_stream_event = ErrorEventData(
                source=f"AgentEventStream.PayloadCreation.{event_type.name}",
                message=f"Failed to process payload: {ve}",
                details=str(actual_payload_content)
            )
            stream_event_type_for_generic_stream = StreamEventType.ERROR_EVENT
        except Exception as e: 
            logger.error(f"AgentEventStream '{self.agent_id}': Unexpected error processing payload for event {event_type.name}: {e}. Payload: {actual_payload_content!r}", exc_info=True)
            typed_payload_for_stream_event = ErrorEventData(
                source=f"AgentEventStream.UnexpectedError.{event_type.name}",
                message=f"Unexpected error: {e}",
                details=traceback.format_exc()
            )
            stream_event_type_for_generic_stream = StreamEventType.ERROR_EVENT


        if typed_payload_for_stream_event and stream_event_type_for_generic_stream:
            try:
                stream_event = StreamEvent(
                    agent_id=event_agent_id, 
                    event_type=stream_event_type_for_generic_stream, 
                    data=typed_payload_for_stream_event
                )
                logger.debug(f"AgentEventStream '{self.agent_id}': Putting StreamEvent of type '{stream_event.event_type.value}' onto generic queue.")
                self._generic_stream_event_internal_q.put(stream_event)
                logger.debug(f"AgentEventStream '{self.agent_id}': Successfully put StreamEvent on generic queue.")
            except Exception as e_se: # pragma: no cover
                logger.error(f"AgentEventStream '{self.agent_id}': Failed to create or enqueue StreamEvent for {stream_event_type_for_generic_stream.value}: {e_se}", exc_info=True)


    async def close(self): # pragma: no cover
        logger.info(f"AgentEventStream for '{self.agent_id}': close() called. Unregistering listeners and signaling internal queues.")
        self._unregister_notifier_listeners() 
        
        queues_to_signal = [
            self._assistant_chunk_internal_q,
            self._assistant_final_message_internal_q,
            self._tool_log_internal_q,
            self._tool_approval_internal_q,
            self._generic_stream_event_internal_q,
        ]
        for q in queues_to_signal:
            try:
                await self._loop.run_in_executor(None, q.put, _AES_INTERNAL_SENTINEL)
            except Exception as e: 
                logger.error(f"AgentEventStream '{self.agent_id}': Error putting sentinel to internal queue {q} during close: {e}", exc_info=True)

    def stream_assistant_chunks(self) -> AsyncIterator[ChunkResponse]: # pragma: no cover
        source_name = f"agent_{self.agent_id}_internal_assistant_chunks"
        logger.debug(f"Providing stream from internal queue: {source_name}.")
        return stream_queue_items(self._assistant_chunk_internal_q, _AES_INTERNAL_SENTINEL, source_name)

    def stream_assistant_final_messages(self) -> AsyncIterator[CompleteResponse]: # pragma: no cover
        source_name = f"agent_{self.agent_id}_internal_assistant_final_messages"
        logger.debug(f"Providing stream from internal queue: {source_name}.")
        return stream_queue_items(self._assistant_final_message_internal_q, _AES_INTERNAL_SENTINEL, source_name)

    def stream_tool_logs(self) -> AsyncIterator[str]: # pragma: no cover
        source_name = f"agent_{self.agent_id}_internal_tool_logs"
        logger.debug(f"Providing stream from internal queue: {source_name}.")
        return stream_queue_items(self._tool_log_internal_q, _AES_INTERNAL_SENTINEL, source_name)

    def stream_pending_tool_approvals(self) -> AsyncIterator[Dict[str, Any]]: # pragma: no cover
        source_name = f"agent_{self.agent_id}_internal_pending_tool_approvals"
        logger.debug(f"Providing stream from internal queue: {source_name}.")
        return stream_queue_items(self._tool_approval_internal_q, _AES_INTERNAL_SENTINEL, source_name)

    async def all_events(self) -> AsyncIterator[StreamEvent]: # pragma: no cover
        logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Starting to stream all_events() from internal generic queue.")
        source_name = f"agent_{self.agent_id}_internal_generic_stream_events"
        
        async for event in stream_queue_items(self._generic_stream_event_internal_q, _AES_INTERNAL_SENTINEL, source_name):
            yield event 
        
        logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Exiting all_events() stream method.")


    def __repr__(self) -> str:
        return f"<AgentEventStream agent_id='{self.agent_id}'>"
