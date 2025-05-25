# file: autobyteus/autobyteus/agent/events/agent_event_queues.py
import asyncio
import logging
from typing import Any, AsyncIterator, Union, Tuple, Optional, List, TYPE_CHECKING, Dict

# Import specific event types for queue annotations where possible
if TYPE_CHECKING:
    from autobyteus.agent.events.agent_events import ( # MODIFIED IMPORT
        UserMessageReceivedEvent, 
        InterAgentMessageReceivedEvent,
        PendingToolInvocationEvent, 
        ToolResultEvent,
        ToolExecutionApprovalEvent,
        BaseEvent
    )
    from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse

logger = logging.getLogger(__name__)

END_OF_STREAM_SENTINEL = object()

class AgentEventQueues:
    """
    Encapsulates all asyncio.Queue instances for an agent, providing a centralized
    mechanism for inter-component communication within the agent's runtime.
    Manages queues for various types of events and data streams.
    """
    def __init__(self, queue_size: int = 0):
        self.user_message_input_queue: asyncio.Queue['UserMessageReceivedEvent'] = asyncio.Queue(maxsize=queue_size)
        self.inter_agent_message_input_queue: asyncio.Queue['InterAgentMessageReceivedEvent'] = asyncio.Queue(maxsize=queue_size)
        self.tool_invocation_request_queue: asyncio.Queue['PendingToolInvocationEvent'] = asyncio.Queue(maxsize=queue_size) 
        self.tool_result_input_queue: asyncio.Queue['ToolResultEvent'] = asyncio.Queue(maxsize=queue_size)
        self.tool_execution_approval_queue: asyncio.Queue['ToolExecutionApprovalEvent'] = asyncio.Queue(maxsize=queue_size)
        self.internal_system_event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_size)

        # Updated output queue types to use proper response objects
        self.assistant_output_chunk_queue: asyncio.Queue[Union['ChunkResponse', object]] = asyncio.Queue(maxsize=queue_size)
        self.assistant_final_message_queue: asyncio.Queue[Union['CompleteResponse', object]] = asyncio.Queue(maxsize=queue_size)
        self.tool_interaction_log_queue: asyncio.Queue[Union[str, object]] = asyncio.Queue(maxsize=queue_size)

        self._input_queues: List[Tuple[str, asyncio.Queue[Any]]] = [
            ("user_message_input_queue", self.user_message_input_queue),
            ("inter_agent_message_input_queue", self.inter_agent_message_input_queue),
            ("tool_invocation_request_queue", self.tool_invocation_request_queue),
            ("tool_result_input_queue", self.tool_result_input_queue),
            ("tool_execution_approval_queue", self.tool_execution_approval_queue),
            ("internal_system_event_queue", self.internal_system_event_queue),
        ]
        
        self._output_queues_map: Dict[str, asyncio.Queue[Union[str, object]]] = {
            "assistant_output_chunk_queue": self.assistant_output_chunk_queue,
            "assistant_final_message_queue": self.assistant_final_message_queue,
            "tool_interaction_log_queue": self.tool_interaction_log_queue,
        }
        logger.info("AgentEventQueues initialized with updated output queue types.")

    async def enqueue_user_message(self, event: 'UserMessageReceivedEvent') -> None:
        await self.user_message_input_queue.put(event)
        logger.debug(f"Enqueued user message received event: {event}")

    async def enqueue_inter_agent_message(self, event: 'InterAgentMessageReceivedEvent') -> None:
        await self.inter_agent_message_input_queue.put(event)
        logger.debug(f"Enqueued inter-agent message received event: {event}")

    async def enqueue_tool_invocation_request(self, event: 'PendingToolInvocationEvent') -> None: 
        await self.tool_invocation_request_queue.put(event)
        logger.debug(f"Enqueued pending tool invocation request event: {event}") 

    async def enqueue_tool_result(self, event: 'ToolResultEvent') -> None:
        await self.tool_result_input_queue.put(event)
        logger.debug(f"Enqueued tool result event: {event}")

    async def enqueue_tool_approval_event(self, event: 'ToolExecutionApprovalEvent') -> None:
        await self.tool_execution_approval_queue.put(event)
        logger.debug(f"Enqueued tool approval event: {event}")

    async def enqueue_internal_system_event(self, event: Any) -> None:
        await self.internal_system_event_queue.put(event)
        logger.debug(f"Enqueued internal system event: {type(event).__name__}")

    async def enqueue_end_of_stream_sentinel_to_output_queue(self, queue_name: str) -> None:
        target_queue = self._output_queues_map.get(queue_name)
        if target_queue:
            await target_queue.put(END_OF_STREAM_SENTINEL)
            logger.debug(f"Enqueued END_OF_STREAM_SENTINEL to output queue: {queue_name}")
        else:
            logger.warning(f"Attempted to enqueue END_OF_STREAM_SENTINEL to unknown output queue: {queue_name}. Available: {list(self._output_queues_map.keys())}")

    async def get_next_input_event(self) -> Optional[Tuple[str, 'BaseEvent']]:
        tasks = [
            asyncio.create_task(queue.get(), name=name)
            for name, queue in self._input_queues if queue is not None
        ]

        if not tasks:
            return None

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        event_tuple: Optional[Tuple[str, 'BaseEvent']] = None

        for task in done:
            queue_name = task.get_name()
            try:
                event_result: Any = task.result() # Get result first
                # It's crucial that items in these queues are indeed BaseEvent instances
                # This check assumes BaseEvent is defined and accessible for isinstance
                from autobyteus.agent.events.agent_events import BaseEvent as AgentBaseEvent # Local import for check
                if isinstance(event_result, AgentBaseEvent):
                    event: 'BaseEvent' = event_result # type: ignore
                    if event_tuple is None: 
                        event_tuple = (queue_name, event)
                        logger.debug(f"Dequeued event from {queue_name}: {type(event).__name__}")
                    else:
                        original_queue = next((q for n, q in self._input_queues if n == queue_name), None)
                        if original_queue:
                            original_queue.put_nowait(event) 
                            logger.warning(f"Re-queued event from {queue_name} as another event was processed first in the same wait cycle.")
                else:
                    logger.error(f"Dequeued item from {queue_name} is not a BaseEvent subclass: {type(event_result)}. Event: {event_result!r}")

            except asyncio.CancelledError:
                logger.info(f"Task for queue {queue_name} was cancelled during get_next_input_event.")
            except TypeError as e: 
                 logger.error(f"Type error processing event from queue {queue_name}: {e}. Event: {task.result()!r}", exc_info=True)
            except Exception as e:
                logger.error(f"Error getting event from queue {queue_name}: {e}", exc_info=True)
        
        for task in pending:
            if not task.done():
                task.cancel()
                try:
                    await task 
                except asyncio.CancelledError:
                    pass 

        return event_tuple

    async def graceful_shutdown(self, timeout: float = 5.0):
        logger.info("Initiating graceful shutdown of AgentEventQueues (joining output queues).")
        output_queues_to_join: List[asyncio.Queue] = [
            self.assistant_output_chunk_queue,
            self.assistant_final_message_queue,
            self.tool_interaction_log_queue,
        ]
        join_tasks = [q.join() for q in output_queues_to_join if q is not None]

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

        logger.info("Logging remaining items in input queues at shutdown:")
        for name, q_obj in self._input_queues:
            if q_obj is not None:
                q_size = q_obj.qsize()
                if q_size > 0:
                    logger.info(f"Input queue '{name}' has {q_size} items remaining at shutdown.")
        
        logger.info("AgentEventQueues graceful shutdown process (joining queues) completed.")
