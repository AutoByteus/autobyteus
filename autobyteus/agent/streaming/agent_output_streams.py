# file: autobyteus/autobyteus/agent/streaming/agent_output_streams.py
import asyncio
import logging
import uuid
import datetime
import traceback 
from typing import AsyncIterator, Dict, Any, Optional, TYPE_CHECKING

from autobyteus.agent.events import AgentEventQueues, END_OF_STREAM_SENTINEL 
from .stream_events import StreamEvent, StreamEventType 
from .queue_streamer import stream_queue_items 

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent # ADDED IMPORT

logger = logging.getLogger(__name__)

class AgentOutputStreams:
    """
    Consumes data from an agent's AgentEventQueues and provides various ways
    to stream this data. This component can be used by API layers, CLI clients,
    or any other consumer of agent output streams.
    """

    def __init__(self, agent: 'Agent'): # MODIFIED CONSTRUCTOR
        """
        Initializes AgentOutputStreams.

        Args:
            agent: The Agent instance from which to stream data. # MODIFIED ARGUMENT
        """
        # Defer direct Agent import for runtime check if not in TYPE_CHECKING block
        # to prevent potential circular dependencies if this module is imported early by agent module.
        # However, direct import at top level is usually fine if Agent doesn't import AgentOutputStreams.
        from autobyteus.agent.agent import Agent as ConcreteAgent # Local import for runtime check
        if not isinstance(agent, ConcreteAgent): # MODIFIED VALIDATION
            raise TypeError(f"AgentOutputStreams requires an Agent instance, got {type(agent).__name__}.")
        
        self._queues: AgentEventQueues = agent.get_event_queues() # MODIFIED INITIALIZATION
        self._agent_id: str = agent.agent_id # MODIFIED INITIALIZATION
        self._sentinel = END_OF_STREAM_SENTINEL 
        logger.info(f"AgentOutputStreams initialized for agent_id '{self._agent_id}'.") # MODIFIED Log

    async def stream_assistant_output_chunks(self) -> AsyncIterator[str]:
        """
        Streams assistant output chunks (raw strings) directly from the
        `assistant_output_chunk_queue`.
        """
        source_name = f"agent_{self._agent_id}_assistant_chunks"
        logger.debug(f"AgentOutputStreams: Starting stream for {source_name}.")
        async for item in stream_queue_items(self._queues.assistant_output_chunk_queue, self._sentinel, source_name):
            yield item
        logger.debug(f"AgentOutputStreams: Finished stream for {source_name}.")

    async def stream_assistant_final_messages(self) -> AsyncIterator[str]:
        """
        Streams assistant final messages (raw strings) directly from the
        `assistant_final_message_queue`.
        """
        source_name = f"agent_{self._agent_id}_assistant_final_messages"
        logger.debug(f"AgentOutputStreams: Starting stream for {source_name}.")
        async for item in stream_queue_items(self._queues.assistant_final_message_queue, self._sentinel, source_name):
            yield item
        logger.debug(f"AgentOutputStreams: Finished stream for {source_name}.")

    async def stream_tool_interaction_logs(self) -> AsyncIterator[str]:
        """
        Streams tool interaction log entries (raw strings) directly from the
        `tool_interaction_log_queue`.
        """
        source_name = f"agent_{self._agent_id}_tool_interaction_logs" # pluralized
        logger.debug(f"AgentOutputStreams: Starting stream for {source_name}.")
        async for item in stream_queue_items(self._queues.tool_interaction_log_queue, self._sentinel, source_name):
            yield item
        logger.debug(f"AgentOutputStreams: Finished stream for {source_name}.")

    async def stream_unified_agent_events(self) -> AsyncIterator[StreamEvent]:
        """
        Consumes multiple raw streams (chunks, final messages, tool logs),
        transforms items into StreamEvent objects, and multiplexes them into a
        single, unified, and typed event stream.
        """
        agent_id_str = self._agent_id or "unknown_agent"
        logger.info(f"AgentOutputStreams (agent_id: {agent_id_str}): Starting unified agent event stream.")

        async def _wrap_string_stream_to_events( # Renamed for clarity
            string_stream_func: callable, # Pass the function that returns the raw stream iterator
            event_type: StreamEventType, 
            data_key: str,
            source_description: str # For logging the wrapped source
        ) -> AsyncIterator[StreamEvent]:
            stream_identity = f"unified_event_wrapper_for_{source_description}_agent_{agent_id_str}"
            logger.debug(f"Starting event wrapping for {stream_identity}.")
            async for raw_item_str in string_stream_func(): # Call the function to get the iterator
                yield StreamEvent(
                    agent_id=self._agent_id,
                    event_type=event_type,
                    data={data_key: raw_item_str}
                )
            logger.debug(f"Event wrapping finished for {stream_identity}.")

        # Map source names to their corresponding stream functions and event creation params
        stream_sources_config = {
            "assistant_chunks": { # Using descriptive keys
                "func": self.stream_assistant_output_chunks, 
                "type": StreamEventType.ASSISTANT_CHUNK, "key": "chunk"
            },
            "assistant_final_messages": { # Using descriptive keys
                "func": self.stream_assistant_final_messages, 
                "type": StreamEventType.ASSISTANT_FINAL_MESSAGE, "key": "message"
            },
            "tool_interaction_logs": { # Using descriptive keys
                "func": self.stream_tool_interaction_logs, 
                "type": StreamEventType.TOOL_INTERACTION_LOG_ENTRY, "key": "log_line"
            },
        }
        
        active_iterators: Dict[str, AsyncIterator[StreamEvent]] = {
            name: _wrap_string_stream_to_events(
                config["func"], config["type"], config["key"], name # type: ignore
            ).__aiter__() for name, config in stream_sources_config.items()
        }
        
        pending_futures: Dict[asyncio.Future, str] = {} 

        def _schedule_next(source_name: str):
            if source_name in active_iterators:
                iterator = active_iterators[source_name]
                task_name = f"unified_event_source_{source_name}_agent_{agent_id_str}"
                future = asyncio.create_task(iterator.__anext__(), name=task_name)
                pending_futures[future] = source_name

        for name in active_iterators.keys():
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
                        logger.debug(f"Unified stream: Source '{source_name}' for agent '{agent_id_str}' fully consumed.")
                        active_iterators.pop(source_name, None) 
                    except Exception as e:
                        logger.error(f"Unified stream: Error from source '{source_name}' for agent '{agent_id_str}': {e}", exc_info=True)
                        yield StreamEvent(
                            agent_id=self._agent_id,
                            event_type=StreamEventType.ERROR_EVENT,
                            data={"source_stream": source_name, "error": str(e), "details": traceback.format_exc()}
                        )
                        active_iterators.pop(source_name, None) 
        
        except asyncio.CancelledError:
            logger.info(f"AgentOutputStreams (agent_id: {agent_id_str}): Unified agent event stream was cancelled.")
            for future in pending_futures.keys():
                if not future.done():
                    future.cancel()
            await asyncio.gather(*pending_futures.keys(), return_exceptions=True)
            raise 
        finally:
            for future_to_cancel in list(pending_futures.keys()): 
                if not future_to_cancel.done():
                    future_to_cancel.cancel()
            if pending_futures: 
                 await asyncio.gather(*pending_futures.keys(), return_exceptions=True)

            logger.info(f"AgentOutputStreams (agent_id: {agent_id_str}): Exiting unified agent event stream.")
