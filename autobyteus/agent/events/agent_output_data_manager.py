# file: autobyteus/autobyteus/agent/events/agent_output_data_manager.py
import asyncio
import logging
from typing import Any, Union, Dict, List, TYPE_CHECKING

# Import specific types for queue annotations where possible
if TYPE_CHECKING:
    from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse

logger = logging.getLogger(__name__)

END_OF_STREAM_SENTINEL = object()

class AgentOutputDataManager:
    """
    Manages asyncio.Queue instances for data produced by the agent, intended
    for external consumption (e.g., by AgentEventStream).
    """
    def __init__(self, queue_size: int = 0):
        # Queues for data/events intended for external consumers
        self.pending_tool_approval_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=queue_size)
        self.assistant_output_chunk_queue: asyncio.Queue[Union['ChunkResponse', object]] = asyncio.Queue(maxsize=queue_size)
        self.assistant_final_message_queue: asyncio.Queue[Union['CompleteResponse', object]] = asyncio.Queue(maxsize=queue_size)
        self.tool_interaction_log_queue: asyncio.Queue[Union[str, object]] = asyncio.Queue(maxsize=queue_size)

        self._output_queues_map: Dict[str, asyncio.Queue[Union[str, Any, object]]] = {
            "assistant_output_chunk_queue": self.assistant_output_chunk_queue,
            "assistant_final_message_queue": self.assistant_final_message_queue,
            "tool_interaction_log_queue": self.tool_interaction_log_queue,
            "pending_tool_approval_queue": self.pending_tool_approval_queue,
        }
        logger.info("AgentOutputDataManager initialized.")

    async def enqueue_pending_tool_approval_data(self, approval_data: Dict[str, Any]) -> None:
        if not isinstance(approval_data, dict) or not all(k in approval_data for k in ["invocation_id", "tool_name", "arguments", "agent_id"]): # pragma: no cover
            logger.warning(f"Attempted to enqueue malformed pending tool approval data: {approval_data}. "
                           "Must be dict with 'invocation_id', 'tool_name', 'arguments', 'agent_id'.")
            return
        await self.pending_tool_approval_queue.put(approval_data)
        logger.debug(f"Enqueued pending tool approval data for invocation_id='{approval_data.get('invocation_id')}'")

    async def enqueue_assistant_chunk(self, chunk: Union['ChunkResponse', object]) -> None:
        await self.assistant_output_chunk_queue.put(chunk)
        if chunk is not END_OF_STREAM_SENTINEL:
             logger.debug(f"Enqueued assistant output chunk: {type(chunk).__name__}")
        else:
             logger.debug("Enqueued END_OF_STREAM_SENTINEL to assistant_output_chunk_queue.")


    async def enqueue_assistant_final_message(self, message: Union['CompleteResponse', object]) -> None:
        await self.assistant_final_message_queue.put(message)
        if message is not END_OF_STREAM_SENTINEL:
            logger.debug(f"Enqueued assistant final message: {type(message).__name__}")
        else:
            logger.debug("Enqueued END_OF_STREAM_SENTINEL to assistant_final_message_queue.")


    async def enqueue_tool_interaction_log(self, log_entry: Union[str, object]) -> None:
        await self.tool_interaction_log_queue.put(log_entry)
        if log_entry is not END_OF_STREAM_SENTINEL:
            logger.debug(f"Enqueued tool interaction log entry: {str(log_entry)[:100]}")
        else:
            logger.debug("Enqueued END_OF_STREAM_SENTINEL to tool_interaction_log_queue.")


    async def enqueue_end_of_stream_sentinel_to_output_queue(self, queue_name: str) -> None:
        target_queue = self._output_queues_map.get(queue_name)
        if target_queue:
            await target_queue.put(END_OF_STREAM_SENTINEL)
            logger.debug(f"Enqueued END_OF_STREAM_SENTINEL to output queue: {queue_name}")
        else: # pragma: no cover
            logger.warning(f"Attempted to enqueue END_OF_STREAM_SENTINEL to unknown output queue: {queue_name}. Available: {list(self._output_queues_map.keys())}")

    async def graceful_shutdown(self, timeout: float = 5.0): # pragma: no cover
        logger.info("Initiating graceful shutdown of AgentOutputDataManager (joining output queues).")
        output_queues_to_join: List[asyncio.Queue] = [
            q for q_name, q in self._output_queues_map.items() if q is not None
        ]
        
        join_tasks = [q.join() for q in output_queues_to_join]

        if not join_tasks: 
            logger.info("No output queues to join during graceful_shutdown.")
        else:
            try:
                await asyncio.wait_for(asyncio.gather(*join_tasks), timeout=timeout)
                logger.info("All output queues joined successfully.")
            except asyncio.TimeoutError: 
                logger.warning(f"Timeout ({timeout}s) waiting for output queues to join during shutdown.")
            except Exception as e: 
                 logger.error(f"Error joining output queues during shutdown: {e}", exc_info=True)
        
        self.log_remaining_items_at_shutdown()
        logger.info("AgentOutputDataManager graceful shutdown process (joining queues) completed.")

    def log_remaining_items_at_shutdown(self): # pragma: no cover
        """Logs remaining items in output queues, typically called during shutdown."""
        logger.info("Logging remaining items in output queues at shutdown (before consumers finish processing sentinels):")
        for name, q_obj in self._output_queues_map.items(): 
            if q_obj is not None:
                q_size = q_obj.qsize()
                if q_size > 0:
                    logger.info(f"Output queue '{name}' has {q_size} items remaining at shutdown.")
