# file: autobyteus/autobyteus/agent/streaming/agent_event_stream.py
import asyncio
import logging
import traceback
import functools # For functools.partial
from typing import AsyncIterator, Dict, Any, TYPE_CHECKING, List, Optional, Callable

from autobyteus.agent.events import AgentEventQueues, END_OF_STREAM_SENTINEL
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
from .queue_streamer import stream_queue_items
from autobyteus.events.event_types import EventType 
from autobyteus.events.event_emitter import EventEmitter # ADDED for inheritance

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent.notifiers import AgentExternalEventNotifier
    from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager

logger = logging.getLogger(__name__)

class AgentEventStream(EventEmitter): # MODIFIED: Inherit from EventEmitter
    """
    Provides access to various output streams from an agent, unified into
    a single `all_events()` stream of `StreamEvent` objects.
    It consumes data from various output queues in AgentEventQueues
    and subscribes to events from AgentExternalEventNotifier.
    """

    def __init__(self, agent: 'Agent'): # pragma: no cover
        super().__init__() # MODIFIED: Call superclass __init__
        
        from autobyteus.agent.agent import Agent as ConcreteAgent 
        if not isinstance(agent, ConcreteAgent):
            raise TypeError(f"AgentEventStream requires an Agent instance, got {type(agent).__name__}.")

        self.agent_id: str = agent.agent_id
        self._queues: AgentEventQueues = agent.get_event_queues() 
        self._sentinel = END_OF_STREAM_SENTINEL
        
        self._pending_tool_approval_queue = self._queues.pending_tool_approval_queue 

        phase_manager: Optional['AgentPhaseManager'] = agent.context.phase_manager
        if phase_manager is None or phase_manager.notifier is None: 
            logger.error(f"AgentEventStream for '{self.agent_id}': AgentPhaseManager or its notifier is not available. Phase events will not be streamed via notifier.")
            self._notifier: Optional['AgentExternalEventNotifier'] = None
        else:
            self._notifier: Optional['AgentExternalEventNotifier'] = phase_manager.notifier
        
        self._notifier_events_bridge_queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        
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
        ]
        # Store handlers for unsubscription
        self._registered_event_handlers: Dict[EventType, Callable] = {}
        self._register_notifier_listeners()
        
        logger.info(f"AgentEventStream initialized for agent_id '{self.agent_id}'. Notifier listener status: {'Active' if self._notifier else 'Inactive'}.")

    def _register_notifier_listeners(self): # pragma: no cover
        if not self._notifier:
            return
        for event_type_to_sub in self._subscribed_notifier_event_types:
            # Create a partial function to pass event_type to the handler
            handler_with_event_type = functools.partial(self._handle_notifier_event, event_type=event_type_to_sub)
            # Store the exact handler instance for later unsubscription
            self._registered_event_handlers[event_type_to_sub] = handler_with_event_type
            try:
                # Use self.subscribe_from as AgentEventStream is now an EventEmitter
                self.subscribe_from(self._notifier, event_type_to_sub, handler_with_event_type)
                logger.debug(f"AgentEventStream '{self.agent_id}': Subscribed to {event_type_to_sub.name} from notifier {self._notifier.object_id}.")
            except Exception as e: 
                logger.error(f"AgentEventStream '{self.agent_id}': Failed to subscribe to {event_type_to_sub.name}: {e}", exc_info=True)
    
    def _unregister_notifier_listeners(self): # pragma: no cover
        if not self._notifier or not self._registered_event_handlers:
            return
        for event_type_to_unsub, handler_to_unsub in self._registered_event_handlers.items():
            try:
                # Use self.unsubscribe_from
                self.unsubscribe_from(self._notifier, event_type_to_unsub, handler_to_unsub)
                logger.debug(f"AgentEventStream '{self.agent_id}': Unsubscribed from {event_type_to_unsub.name} from notifier {self._notifier.object_id}.")
            except Exception as e: 
                logger.warning(f"AgentEventStream '{self.agent_id}': Failed to unsubscribe from {event_type_to_unsub.name} (may be harmless): {e}")
        self._registered_event_handlers.clear()

    # MODIFIED: Signature to match EventEmitter's dispatch and include event_type via partial
    async def _handle_notifier_event(self, *args, event_type: EventType, object_id: Optional[str] = None, **payload: Any): # pragma: no cover
        # object_id is the ID of the notifier that emitted the event.
        # args is for any positional arguments passed by emit after event_type and target (currently none from Notifier)
        # payload contains the keyword arguments from the notifier's emit call.
        
        logger.debug(f"AgentEventStream '{self.agent_id}': Handling notifier event. event_type='{event_type.name}', emitter_object_id='{object_id}', payload_keys='{list(payload.keys())}'")
        
        event_agent_id = payload.get("agent_id", self.agent_id) 
        stream_event: Optional[StreamEvent] = None

        # All subscribed events are phase events and become AGENT_PHASE_UPDATE StreamEvents.
        # The `payload` from the original EventType (which includes things like error_message, tool_name, etc.,
        # but NOT tool_details for AWAITING_TOOL_APPROVAL phase as per last agreement)
        # will be passed into the StreamEvent's data field.
        if event_type.name.startswith("AGENT_PHASE_"):
            new_phase_val = payload.get("new_phase")
            old_phase_val = payload.get("old_phase")
            
            additional_data_for_stream = {
                k: v for k, v in payload.items() 
                if k not in ["agent_id", "new_phase", "old_phase"] 
            }
            stream_event_data = {
                "agent_id": event_agent_id, 
                "phase": new_phase_val,
                "old_phase": old_phase_val,
            }
            if additional_data_for_stream:
                stream_event_data.update(additional_data_for_stream)
            
            stream_event = StreamEvent(
                agent_id=event_agent_id, 
                event_type=StreamEventType.AGENT_PHASE_UPDATE,
                data=stream_event_data
            )
            logger.debug(f"AgentEventStream '{self.agent_id}': Bridging {event_type.name} as AGENT_PHASE_UPDATE StreamEvent. New phase: {new_phase_val}, Data keys: {list(stream_event_data.keys())}")
        
        else: 
            # This case should ideally not be hit if _subscribed_notifier_event_types is accurate
            logger.warning(f"AgentEventStream '{self.agent_id}': Received subscribed event type '{event_type.name}' that is not a phase event. This event will be ignored by this handler logic.")
            return

        if stream_event: 
            try:
                await self._notifier_events_bridge_queue.put(stream_event)
            except Exception as e:  
                 logger.error(f"AgentEventStream '{self.agent_id}': Error putting StreamEvent (from {event_type.name}) to bridge queue: {e}", exc_info=True)

    async def _stream_notifier_events_from_bridge_queue(self) -> AsyncIterator[StreamEvent]: # pragma: no cover
        source_name = f"notifier_events_bridge_agent_{self.agent_id}"
        logger.debug(f"AgentEventStream '{self.agent_id}': Starting to stream from '{source_name}'.")
        async for event in stream_queue_items(self._notifier_events_bridge_queue, self._sentinel, source_name):
            yield event
        logger.debug(f"AgentEventStream '{self.agent_id}': Finished streaming from '{source_name}'.")

    async def close(self): # pragma: no cover
        logger.info(f"AgentEventStream for '{self.agent_id}': close() called. Unregistering listeners and signaling bridge queue.")
        self._unregister_notifier_listeners() # Ensures listeners are removed
        try:
            await self._notifier_events_bridge_queue.put(self._sentinel)
        except Exception as e: 
            logger.error(f"AgentEventStream '{self.agent_id}': Error putting sentinel to notifier events bridge queue during close: {e}", exc_info=True)
        # Call super().close() if EventEmitter had a close method, but it doesn't.

    def stream_assistant_chunks(self) -> AsyncIterator[ChunkResponse]: # pragma: no cover
        source_name = f"agent_{self.agent_id}_direct_assistant_chunks"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.assistant_output_chunk_queue, self._sentinel, source_name)

    def stream_assistant_final_messages(self) -> AsyncIterator[CompleteResponse]: # pragma: no cover
        source_name = f"agent_{self.agent_id}_direct_assistant_final_messages"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.assistant_final_message_queue, self._sentinel, source_name)

    def stream_tool_logs(self) -> AsyncIterator[str]: # pragma: no cover
        source_name = f"agent_{self.agent_id}_direct_tool_logs"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.tool_interaction_log_queue, self._sentinel, source_name)

    async def _wrap_assistant_chunks_to_events(self) -> AsyncIterator[StreamEvent]: # pragma: no cover
        source_description = "assistant_chunks_for_unified_stream"
        stream_identity = f"event_wrapper_for_{source_description}_agent_{self.agent_id}"
        logger.debug(f"Starting event wrapping for {stream_identity}.")
        async for chunk_response in self.stream_assistant_chunks(): 
            if isinstance(chunk_response, ChunkResponse): 
                yield StreamEvent(
                    agent_id=self.agent_id,
                    event_type=StreamEventType.ASSISTANT_CHUNK,
                    data={"chunk": chunk_response.content, "usage": chunk_response.usage, "is_complete": chunk_response.is_complete}
                )
            else:  
                logger.warning(f"Expected ChunkResponse in {stream_identity}, got {type(chunk_response)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_assistant_final_messages_to_events(self) -> AsyncIterator[StreamEvent]: # pragma: no cover
        source_description = "assistant_final_messages_for_unified_stream"
        stream_identity = f"event_wrapper_for_{source_description}_agent_{self.agent_id}"
        logger.debug(f"Starting event wrapping for {stream_identity}.")
        async for complete_response in self.stream_assistant_final_messages(): 
            if isinstance(complete_response, CompleteResponse): 
                yield StreamEvent(
                    agent_id=self.agent_id,
                    event_type=StreamEventType.ASSISTANT_FINAL_MESSAGE,
                    data={"message": complete_response.content, "usage": complete_response.usage}
                )
            else:  
                logger.warning(f"Expected CompleteResponse in {stream_identity}, got {type(complete_response)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_tool_logs_to_events(self) -> AsyncIterator[StreamEvent]: # pragma: no cover
        source_description = "tool_interaction_logs_for_unified_stream"
        stream_identity = f"event_wrapper_for_{source_description}_agent_{self.agent_id}"
        logger.debug(f"Starting event wrapping for {stream_identity}.")
        async for raw_item_str in self.stream_tool_logs(): 
            if isinstance(raw_item_str, str): 
                yield StreamEvent(
                    agent_id=self.agent_id,
                    event_type=StreamEventType.TOOL_INTERACTION_LOG_ENTRY,
                    data={"log_line": raw_item_str}
                )
            else:  
                logger.warning(f"Expected str in {stream_identity}, got {type(raw_item_str)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_pending_tool_approvals_from_queue(self) -> AsyncIterator[StreamEvent]:  # pragma: no cover
        source_description = "pending_tool_approvals_for_unified_stream" 
        stream_identity = f"event_wrapper_for_{source_description}_agent_{self.agent_id}"
        logger.debug(f"Starting event wrapping for {stream_identity}.")
        
        async for approval_data_dict in stream_queue_items(self._pending_tool_approval_queue, self._sentinel, stream_identity):
            if isinstance(approval_data_dict, dict):
                event_agent_id = approval_data_dict.get("agent_id", self.agent_id) 
                yield StreamEvent(
                    agent_id=event_agent_id,
                    event_type=StreamEventType.TOOL_APPROVAL_REQUESTED, 
                    data=approval_data_dict 
                )
            else: 
                logger.warning(f"Expected dict in {stream_identity} (from pending_tool_approval_queue), got {type(approval_data_dict)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")


    async def all_events(self) -> AsyncIterator[StreamEvent]: # pragma: no cover
        logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Starting to stream all_events().")

        iterators_map: Dict[str, AsyncIterator[StreamEvent]] = {
            "assistant_chunks": self._wrap_assistant_chunks_to_events().__aiter__(),
            "assistant_final_messages": self._wrap_assistant_final_messages_to_events().__aiter__(),
            "tool_interaction_logs": self._wrap_tool_logs_to_events().__aiter__(),
            "pending_tool_approvals": self._wrap_pending_tool_approvals_from_queue().__aiter__(), 
            "notifier_bridge": self._stream_notifier_events_from_bridge_queue().__aiter__(), 
        }
        
        pending_futures: Dict[asyncio.Future, str] = {}

        def _schedule_next(source_name: str):
            if source_name in iterators_map: 
                iterator = iterators_map[source_name]
                task_name = f"all_events_source_{source_name}_agent_{self.agent_id}"
                future = asyncio.create_task(iterator.__anext__(), name=task_name)
                pending_futures[future] = source_name
            else:  
                 logger.debug(f"AgentEventStream '{self.agent_id}': Source '{source_name}' no longer in iterators_map (likely exhausted or error), not scheduling next for it.")

        for name in iterators_map.keys():
            _schedule_next(name)

        try:
            while pending_futures:
                done_futures, _ = await asyncio.wait(
                    list(pending_futures.keys()), 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for future in done_futures:
                    source_name = pending_futures.pop(future) 
                    try:
                        event: StreamEvent = future.result()
                        yield event
                        _schedule_next(source_name) 
                    except StopAsyncIteration:
                        logger.debug(f"AgentEventStream: Source '{source_name}' for agent '{self.agent_id}' (all_events) fully consumed.")
                        iterators_map.pop(source_name, None) 
                    except asyncio.CancelledError: 
                        logger.info(f"AgentEventStream: Task for source '{source_name}' for agent '{self.agent_id}' (all_events) was cancelled.")
                        iterators_map.pop(source_name, None) 
                    except Exception as e: 
                        logger.error(f"AgentEventStream: Error from source '{source_name}' for agent '{self.agent_id}' (all_events): {e}", exc_info=True)
                        yield StreamEvent(
                            agent_id=self.agent_id,
                            event_type=StreamEventType.ERROR_EVENT,
                            data={"source_stream": source_name, "error": str(e), "details": traceback.format_exc()}
                        )
                        iterators_map.pop(source_name, None) 
        
        except asyncio.CancelledError: 
            logger.info(f"AgentEventStream (agent_id: {self.agent_id}): all_events() stream was cancelled externally.")
            raise
        finally: 
            logger.debug(f"AgentEventStream (agent_id: {self.agent_id}): all_events() entering finally block. Pending futures: {len(pending_futures)}")
            active_futures_to_cancel = [f for f in pending_futures.keys() if not f.done()]
            for future_to_cancel in active_futures_to_cancel:  
                if not future_to_cancel.done(): 
                    future_to_cancel.cancel()
            
            if active_futures_to_cancel: 
                 results = await asyncio.gather(*active_futures_to_cancel, return_exceptions=True)
                 for i, res in enumerate(results): 
                     fut_task_to_log = active_futures_to_cancel[i]
                     task_name_for_log = fut_task_to_log.get_name() 
                     if isinstance(res, Exception) and not isinstance(res, asyncio.CancelledError): 
                          logger.warning(f"AgentEventStream '{self.agent_id}': Exception during cleanup of future for task '{task_name_for_log}': {res}")
                     elif isinstance(res, asyncio.CancelledError):
                          logger.debug(f"AgentEventStream '{self.agent_id}': Task '{task_name_for_log}' confirmed cancelled during cleanup.")
            
            await self.close() 
            logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Exiting all_events() stream method.")

    def __repr__(self) -> str:
        return f"<AgentEventStream agent_id='{self.agent_id}'>"

