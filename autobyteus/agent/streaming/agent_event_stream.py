# file: autobyteus/autobyteus/agent/streaming/agent_event_stream.py
import asyncio
import logging
import traceback
from typing import AsyncIterator, Dict, Any, TYPE_CHECKING

from autobyteus.agent.events import AgentEventQueues, END_OF_STREAM_SENTINEL
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
from .queue_streamer import stream_queue_items

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent

logger = logging.getLogger(__name__)

class AgentEventStream:
    """
    Provides access to various output streams from an agent.

    - For the unified, processed stream of standardized `StreamEvent` objects,
      use the `all_events()` method.
        - `async for event in streamer.all_events(): ...`

    - For direct access to raw, unprocessed stream types (like `ChunkResponse`
      or raw log strings), use specific methods:
        - `streamer.stream_assistant_chunks() -> AsyncIterator[ChunkResponse]`
        - `streamer.stream_assistant_final_messages() -> AsyncIterator[CompleteResponse]`
        - `streamer.stream_tool_logs() -> AsyncIterator[str]`
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
        
        logger.info(f"AgentEventStream initialized for agent_id '{self.agent_id}'. Provides direct stream methods and all_events().")

    # --- Raw Stream Methods ---
    def stream_assistant_chunks(self) -> AsyncIterator[ChunkResponse]:
        """Asynchronously streams raw assistant output chunks (ChunkResponse objects)."""
        source_name = f"agent_{self.agent_id}_direct_assistant_chunks"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.assistant_output_chunk_queue, self._sentinel, source_name)

    def stream_assistant_final_messages(self) -> AsyncIterator[CompleteResponse]:
        """Asynchronously streams raw assistant final messages (CompleteResponse objects)."""
        source_name = f"agent_{self.agent_id}_direct_assistant_final_messages"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.assistant_final_message_queue, self._sentinel, source_name)

    def stream_tool_logs(self) -> AsyncIterator[str]:
        """Asynchronously streams raw tool interaction log entries (strings)."""
        source_name = f"agent_{self.agent_id}_direct_tool_logs"
        logger.debug(f"Providing raw stream: {source_name}.")
        return stream_queue_items(self._queues.tool_interaction_log_queue, self._sentinel, source_name)

    # --- Unified Event Stream Logic ---

    async def _wrap_assistant_chunks_to_events(self) -> AsyncIterator[StreamEvent]:
        """Internal: Wraps raw assistant chunks from self.stream_assistant_chunks() into StreamEvents."""
        source_description = "assistant_chunks_for_unified_stream"
        stream_identity = f"event_wrapper_for_{source_description}_agent_{self.agent_id}"
        logger.debug(f"Starting event wrapping for {stream_identity}.")
        async for chunk_response in self.stream_assistant_chunks(): # Call direct method
            if isinstance(chunk_response, ChunkResponse):
                yield StreamEvent(
                    agent_id=self.agent_id,
                    event_type=StreamEventType.ASSISTANT_CHUNK,
                    data={"chunk": chunk_response.content, "usage": chunk_response.usage, "is_complete": chunk_response.is_complete}
                )
            else: 
                logger.warning(f"Expected ChunkResponse in {stream_identity}, got {type(chunk_response)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_assistant_final_messages_to_events(self) -> AsyncIterator[StreamEvent]:
        """Internal: Wraps raw assistant final messages from self.stream_assistant_final_messages() into StreamEvents."""
        source_description = "assistant_final_messages_for_unified_stream"
        stream_identity = f"event_wrapper_for_{source_description}_agent_{self.agent_id}"
        logger.debug(f"Starting event wrapping for {stream_identity}.")
        async for complete_response in self.stream_assistant_final_messages(): # Call direct method
            if isinstance(complete_response, CompleteResponse):
                yield StreamEvent(
                    agent_id=self.agent_id,
                    event_type=StreamEventType.ASSISTANT_FINAL_MESSAGE,
                    data={"message": complete_response.content, "usage": complete_response.usage}
                )
            else: 
                logger.warning(f"Expected CompleteResponse in {stream_identity}, got {type(complete_response)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def _wrap_tool_logs_to_events(self) -> AsyncIterator[StreamEvent]:
        """Internal: Wraps raw tool logs from self.stream_tool_logs() into StreamEvents."""
        source_description = "tool_interaction_logs_for_unified_stream"
        stream_identity = f"event_wrapper_for_{source_description}_agent_{self.agent_id}"
        logger.debug(f"Starting event wrapping for {stream_identity}.")
        async for raw_item_str in self.stream_tool_logs(): # Call direct method
            if isinstance(raw_item_str, str):
                yield StreamEvent(
                    agent_id=self.agent_id,
                    event_type=StreamEventType.TOOL_INTERACTION_LOG_ENTRY,
                    data={"log_line": raw_item_str}
                )
            else: 
                logger.warning(f"Expected str in {stream_identity}, got {type(raw_item_str)}")
        logger.debug(f"Event wrapping finished for {stream_identity}.")

    async def all_events(self) -> AsyncIterator[StreamEvent]:
        """
        Provides a comprehensive stream of all significant agent events.
        It consumes multiple raw output streams (assistant chunks, final messages, tool logs) 
        using its own direct stream methods (e.g., self.stream_assistant_chunks()), 
        transforms their items into standardized StreamEvent objects, and multiplexes them 
        into this single, typed event stream.
        """
        logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Starting to stream all_events().")

        iterators_map: Dict[str, AsyncIterator[StreamEvent]] = {
            "assistant_chunks": self._wrap_assistant_chunks_to_events().__aiter__(),
            "assistant_final_messages": self._wrap_assistant_final_messages_to_events().__aiter__(),
            "tool_interaction_logs": self._wrap_tool_logs_to_events().__aiter__(),
        }
        
        pending_futures: Dict[asyncio.Future, str] = {}

        def _schedule_next(source_name: str):
            if source_name in iterators_map:
                iterator = iterators_map[source_name]
                task_name = f"all_events_source_{source_name}_agent_{self.agent_id}"
                future = asyncio.create_task(iterator.__anext__(), name=task_name)
                pending_futures[future] = source_name

        for name in iterators_map.keys():
            _schedule_next(name)

        try:
            while pending_futures:
                done_futures, _ = await asyncio.wait(
                    pending_futures.keys(),
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
                    except Exception as e:
                        logger.error(f"AgentEventStream: Error from source '{source_name}' for agent '{self.agent_id}' (all_events): {e}", exc_info=True)
                        yield StreamEvent(
                            agent_id=self.agent_id,
                            event_type=StreamEventType.ERROR_EVENT,
                            data={"source_stream": source_name, "error": str(e), "details": traceback.format_exc()}
                        )
                        iterators_map.pop(source_name, None)
        
        except asyncio.CancelledError:
            logger.info(f"AgentEventStream (agent_id: {self.agent_id}): all_events() stream was cancelled.")
            for future_to_cancel in list(pending_futures.keys()): 
                if not future_to_cancel.done():
                    future_to_cancel.cancel()
            if pending_futures:
                 await asyncio.gather(*pending_futures.keys(), return_exceptions=True)
            raise
        finally:
            for future_to_cancel in list(pending_futures.keys()):
                if not future_to_cancel.done():
                    future_to_cancel.cancel()
            if pending_futures:
                 await asyncio.gather(*pending_futures.keys(), return_exceptions=True)
            
            logger.info(f"AgentEventStream (agent_id: {self.agent_id}): Exiting all_events() stream.")

    def __repr__(self) -> str:
        return f"<AgentEventStream agent_id='{self.agent_id}'>"
