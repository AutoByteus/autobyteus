# file: autobyteus/autobyteus/agent/events/agent_event_queues.py
import asyncio
import logging
from typing import Any, AsyncIterator, Union, Tuple, Optional, List, TYPE_CHECKING, Dict, Set

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
        logger.debug(f"get_next_input_event: Checking queue sizes before creating tasks...")
        for name, q_obj in self._input_queues:
            if q_obj is not None:
                logger.debug(f"get_next_input_event: Queue '{name}' qsize: {q_obj.qsize()}")

        # Create tasks to get an item from each input queue
        created_tasks: List[asyncio.Task] = [
            asyncio.create_task(queue.get(), name=name)
            for name, queue in self._input_queues if queue is not None
        ]

        if not created_tasks:
            logger.warning("get_next_input_event: No input queues available to create tasks from. Returning None.")
            return None
        
        logger.debug(f"get_next_input_event: Created {len(created_tasks)} tasks for queues: {[t.get_name() for t in created_tasks]}. Awaiting asyncio.wait...")
        
        event_tuple: Optional[Tuple[str, 'BaseEvent']] = None
        done_tasks_from_wait: Set[asyncio.Task] = set()
        # pending_tasks_from_wait will contain tasks not in done_tasks_from_wait from the original created_tasks list

        try:
            # Wait for at least one of the tasks to complete
            done_tasks_from_wait, pending_tasks_from_wait = await asyncio.wait(
                created_tasks, return_when=asyncio.FIRST_COMPLETED
            )
            
            logger.debug(f"get_next_input_event: asyncio.wait returned. Done tasks: {len(done_tasks_from_wait)}, Pending tasks: {len(pending_tasks_from_wait)}.")
            
            if done_tasks_from_wait:
                for i, task_in_done in enumerate(done_tasks_from_wait):
                    logger.debug(f"get_next_input_event: Processing done task #{i+1} (name: {task_in_done.get_name()})")
            
            for task in done_tasks_from_wait:
                queue_name = task.get_name()
                try:
                    event_result: Any = task.result() 
                    logger.debug(f"get_next_input_event: Task for queue '{queue_name}' completed. Result type: {type(event_result).__name__}, Result: {str(event_result)[:100]}")
                    
                    from autobyteus.agent.events.agent_events import BaseEvent as AgentBaseEvent 
                    if isinstance(event_result, AgentBaseEvent):
                        event: 'BaseEvent' = event_result 
                        if event_tuple is None: 
                            event_tuple = (queue_name, event)
                            logger.debug(f"get_next_input_event: Dequeued event from {queue_name}: {type(event).__name__}")
                        else:
                            # This case should be rare with FIRST_COMPLETED if events are handled one by one
                            original_queue = next((q for n, q in self._input_queues if n == queue_name), None)
                            if original_queue:
                                original_queue.put_nowait(event) 
                                logger.warning(f"get_next_input_event: Re-queued event from {queue_name} (type {type(event).__name__}) as another event was processed first in the same wait cycle.")
                    else:
                        logger.error(f"get_next_input_event: Dequeued item from {queue_name} is not a BaseEvent subclass: {type(event_result)}. Event: {event_result!r}")

                except asyncio.CancelledError:
                     logger.info(f"get_next_input_event: Task for queue {queue_name} (from done set) was cancelled during result processing.")
                except Exception as e: 
                    logger.error(f"get_next_input_event: Error processing result from task for queue {queue_name} (from done set): {e}", exc_info=True)
            
            # Cancel tasks that were pending after asyncio.wait returned
            # These are tasks that didn't complete to satisfy FIRST_COMPLETED
            # This cancellation is part of normal operation, not necessarily due to external cancellation of get_next_input_event
            if pending_tasks_from_wait:
                logger.debug(f"get_next_input_event: Cancelling {len(pending_tasks_from_wait)} pending tasks from asyncio.wait.")
                for task_in_pending in pending_tasks_from_wait:
                    if not task_in_pending.done():
                        task_in_pending.cancel()
                        # These tasks are locally managed; awaiting them here is for this specific call's cleanup.
                        # If get_next_input_event itself is cancelled, the broader 'finally' block handles created_tasks.
                        try:
                            await task_in_pending 
                        except asyncio.CancelledError:
                            pass # Expected

        except asyncio.CancelledError:
            logger.debug("get_next_input_event: Coroutine itself was cancelled (e.g., by AgentRuntime timeout). All created tasks will be cancelled in finally.")
            raise # Propagate CancelledError to allow AgentRuntime's wait_for to handle it.
        
        finally:
            # This block executes whether get_next_input_event exits normally,
            # via an exception, or due to being cancelled.
            # Its purpose is to ensure that ALL tasks created by *this specific invocation*
            # of get_next_input_event are cleaned up (cancelled and awaited).
            logger.debug(f"get_next_input_event: Entering finally block. Cleaning up {len(created_tasks)} originally created tasks.")
            
            cleanup_awaits = []
            for task_to_clean in created_tasks:
                if not task_to_clean.done():
                    logger.debug(f"get_next_input_event (finally): Task '{task_to_clean.get_name()}' is not done, cancelling.")
                    task_to_clean.cancel()
                    cleanup_awaits.append(task_to_clean)
                else:
                    # If task is done, ensure its result/exception is retrieved to avoid "never retrieved" warnings.
                    # This is particularly for tasks that might have completed but weren't the one selected by FIRST_COMPLETED,
                    # or if an error occurred after asyncio.wait but before this finally block.
                    # However, if it was in done_tasks_from_wait, its result was already accessed.
                    # This part is delicate; excessive result() calls can error if already retrieved or if it errored.
                    # Let's only focus on awaiting tasks that were added to cleanup_awaits (i.e., were just cancelled).
                    logger.debug(f"get_next_input_event (finally): Task '{task_to_clean.get_name()}' is already done.")

            if cleanup_awaits:
                logger.debug(f"get_next_input_event (finally): Awaiting {len(cleanup_awaits)} cancelled tasks.")
                # Allow exceptions during gather (e.g., if a task doesn't handle CancelledError cleanly)
                # but don't let them stop the cleanup of other tasks.
                results = await asyncio.gather(*cleanup_awaits, return_exceptions=True)
                for i, result in enumerate(results):
                    task_name_for_log = cleanup_awaits[i].get_name()
                    if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                        logger.warning(f"get_next_input_event (finally): Exception during cleanup of task '{task_name_for_log}': {result!r}")
                    elif isinstance(result, asyncio.CancelledError):
                         logger.debug(f"get_next_input_event (finally): Task '{task_name_for_log}' confirmed cancelled.")
            
            logger.debug(f"get_next_input_event: Finished finally block task cleanup.")

        logger.debug(f"get_next_input_event: Returning event_tuple: {type(event_tuple[1]).__name__ if event_tuple else 'None'}")
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

