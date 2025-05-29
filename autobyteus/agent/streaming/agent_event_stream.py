# file: autobyteus/autobyteus/agent/streaming/agent_event_stream.py
import asyncio
import logging
import traceback
from typing import AsyncIterator, Dict, Any, TYPE_CHECKING, List, Optional, Callable, Union

from autobyteus.agent.events import AgentEventQueues, END_OF_STREAM_SENTINEL
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
from .queue_streamer import stream_queue_items

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent

logger = logging.getLogger(__name__)

class AgentEventStream:
    """
    Provides access to various output streams from an agent, unified into
    a single `all_events()` stream of `StreamEvent` objects.
    It consumes data from various output queues in AgentEventQueues:
    - assistant_output_chunk_queue
    - assistant_final_message_queue
    - tool_interaction_log_queue
    - pending_tool_approval_queue (for tool approval request data)
    It transforms items from these queues into standardized StreamEvent objects.
    Agent status changes are NOT explicitly streamed as StreamEvents by this component.
    """

    def __init__(self, agent: 'Agent'):
        """
        Initializes AgentEventStream.

        Args:
            agent: The Agent instance from which to stream events and outputs.
        """
        from autobyteus.agent.agent import Agent as ConcreteAgent 
        if not isinstance(agent, ConcreteAgent):
            raise TypeError(f"AgentEventStream requires an Agent instance, got {type(agent).__name__}.")

        self.agent_id: str = agent.agent_id
        self._queues: AgentEventQueues = agent.get_event_queues()
        self._sentinel = END_OF_STREAM_SENTINEL
        
        self._pending_tool_approval_queue = self._queues.pending_tool_approval_queue
        # REMOVED: _agent_status_update_queue attribute
        # REMOVED: Attributes related to status manager subscription (_status_manager, _status_updates_bridge_queue, _subscribed_status_handlers)
        # REMOVED: Call to _subscribe_to_status_manager()
        
        logger.info(f"AgentEventStream initialized for agent_id '{self.agent_id}'. Provides unified all_events() stream.")


    async def close(self): 
        logger.info(f"AgentEventStream for '{self.agent_id}': close() called. No active subscriptions to clean up in this version.")
        # REMOVED: Logic for unsubscribing from status manager and signaling bridge queue.

    # --- Raw Stream Methods ---
    def stream_assistant_chunks(self) -> AsyncIterator[ChunkResponse]:
        source_name = f"agent_{self.agent_id}_direct_assistant_chunks"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.assistant_output_chunk_queue, self._sentinel, source_name)

    def stream_assistant_final_messages(self) -> AsyncIterator[CompleteResponse]:
        source_name = f"agent_{self.agent_id}_direct_assistant_final_messages"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.assistant_final_message_queue, self._sentinel, source_name)

    def stream_tool_logs(self) -> AsyncIterator[str]:
        source_name = f"agent_{self.agent_id}_direct_tool_logs"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.tool_interaction_log_queue, self._sentinel, source_name)

    # --- Unified Event Stream Logic ---

    async def _wrap_assistant_chunks_to_events(self) -> AsyncIterator[StreamEvent]:
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
            else:  # pragma: no cover
                logger.warning(f"Expected ChunkResponse in {stream_identity}, got {type(chunk_response)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_assistant_final_messages_to_events(self) -> AsyncIterator[StreamEvent]:
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
            else:  # pragma: no cover
                logger.warning(f"Expected CompleteResponse in {stream_identity}, got {type(complete_response)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_tool_logs_to_events(self) -> AsyncIterator[StreamEvent]:
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
            else:  # pragma: no cover
                logger.warning(f"Expected str in {stream_identity}, got {type(raw_item_str)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_pending_tool_approvals_from_queue(self) -> AsyncIterator[StreamEvent]: 
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
            else: # pragma: no cover
                logger.warning(f"Expected dict in {stream_identity} (from pending_tool_approval_queue), got {type(approval_data_dict)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    # REMOVED: _wrap_agent_status_updates_from_queue method
    # REMOVED: _stream_status_updates_from_bridge_queue method (was for the direct subscription model)

    async def all_events(self) -> AsyncIterator[StreamEvent]:
        logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Starting to stream all_events().")

        iterators_map: Dict[str, AsyncIterator[StreamEvent]] = {
            "assistant_chunks": self._wrap_assistant_chunks_to_events().__aiter__(),
            "assistant_final_messages": self._wrap_assistant_final_messages_to_events().__aiter__(),
            "tool_interaction_logs": self._wrap_tool_logs_to_events().__aiter__(),
            "pending_tool_approvals": self._wrap_pending_tool_approvals_from_queue().__aiter__(),
            # REMOVED: "agent_status_updates" or "status_updates" source from map
        }
        
        pending_futures: Dict[asyncio.Future, str] = {}

        def _schedule_next(source_name: str):
            if source_name in iterators_map:
                iterator = iterators_map[source_name]
                task_name = f"all_events_source_{source_name}_agent_{self.agent_id}"
                future = asyncio.create_task(iterator.__anext__(), name=task_name)
                pending_futures[future] = source_name
            else: 
                 logger.debug(f"Source '{source_name}' no longer in iterators_map (likely exhausted or error), not scheduling next for it.")

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
                    except Exception as e: # pragma: no cover
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
                future_to_cancel.cancel()
            
            if active_futures_to_cancel:
                 results = await asyncio.gather(*active_futures_to_cancel, return_exceptions=True)
                 for i, res in enumerate(results): 
                     fut_name_task = active_futures_to_cancel[i]
                     original_source_name = pending_futures.get(fut_name_task, fut_name_task.get_name()) # Should be fut_name_task.get_name() here

                     if isinstance(res, Exception) and not isinstance(res, asyncio.CancelledError): # pragma: no cover
                          logger.warning(f"Exception during cleanup of future for source '{original_source_name}': {res}")
            
            await self.close() # Call close, though it does less now
            logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Exiting all_events() stream method.")

    def __repr__(self) -> str:
        return f"<AgentEventStream agent_id='{self.agent_id}'>"

