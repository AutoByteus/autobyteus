# file: autobyteus/autobyteus/agent/events/agent_input_event_queue_manager.py
import asyncio
import logging
from typing import Any, AsyncIterator, Union, Tuple, Optional, List, TYPE_CHECKING, Dict, Set

# Import specific event types for queue annotations where possible
if TYPE_CHECKING:
    from autobyteus.agent.events.agent_events import (
        UserMessageReceivedEvent,
        InterAgentMessageReceivedEvent,
        PendingToolInvocationEvent,
        ToolResultEvent,
        ToolExecutionApprovalEvent,
        BaseEvent,

    )

logger = logging.getLogger(__name__)

class AgentInputEventQueueManager:
    """
    Manages asyncio.Queue instances for events consumed by the AgentRuntime's
    main event loop. This class focuses solely on queues for internal agent processing.
    """
    def __init__(self, queue_size: int = 0):
        self.user_message_input_queue: asyncio.Queue['UserMessageReceivedEvent'] = asyncio.Queue(maxsize=queue_size)
        self.inter_agent_message_input_queue: asyncio.Queue['InterAgentMessageReceivedEvent'] = asyncio.Queue(maxsize=queue_size)
        self.tool_invocation_request_queue: asyncio.Queue['PendingToolInvocationEvent'] = asyncio.Queue(maxsize=queue_size)
        self.tool_result_input_queue: asyncio.Queue['ToolResultEvent'] = asyncio.Queue(maxsize=queue_size)
        self.tool_execution_approval_queue: asyncio.Queue['ToolExecutionApprovalEvent'] = asyncio.Queue(maxsize=queue_size)
        self.internal_system_event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_size) # For lifecycle, init events

        self._input_queues: List[Tuple[str, asyncio.Queue[Any]]] = [
            ("user_message_input_queue", self.user_message_input_queue),
            ("inter_agent_message_input_queue", self.inter_agent_message_input_queue),
            ("tool_invocation_request_queue", self.tool_invocation_request_queue),
            ("tool_result_input_queue", self.tool_result_input_queue),
            ("tool_execution_approval_queue", self.tool_execution_approval_queue),
            ("internal_system_event_queue", self.internal_system_event_queue),
        ]
        logger.info("AgentInputEventQueueManager initialized.")

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

    async def get_next_input_event(self) -> Optional[Tuple[str, 'BaseEvent']]: # type: ignore[type-var]
        # Logger messages will be updated in subsequent steps if needed
        logger.debug(f"get_next_input_event: Checking queue sizes before creating tasks...")
        for name, q_obj in self._input_queues:
            if q_obj is not None: # pragma: no cover
                logger.debug(f"get_next_input_event: Queue '{name}' qsize: {q_obj.qsize()}")

        created_tasks: List[asyncio.Task] = [
            asyncio.create_task(queue.get(), name=name)
            for name, queue in self._input_queues if queue is not None
        ]

        if not created_tasks: # pragma: no cover
            logger.warning("get_next_input_event: No input queues available to create tasks from. Returning None.")
            return None
        
        logger.debug(f"get_next_input_event: Created {len(created_tasks)} tasks for queues: {[t.get_name() for t in created_tasks]}. Awaiting asyncio.wait...")
        
        event_tuple: Optional[Tuple[str, 'BaseEvent']] = None # type: ignore[type-var]
        done_tasks_from_wait: Set[asyncio.Task] = set()
        
        try:
            done_tasks_from_wait, pending_tasks_from_wait = await asyncio.wait(
                created_tasks, return_when=asyncio.FIRST_COMPLETED
            )
            
            logger.debug(f"get_next_input_event: asyncio.wait returned. Done tasks: {len(done_tasks_from_wait)}, Pending tasks: {len(pending_tasks_from_wait)}.")
            
            if done_tasks_from_wait: # pragma: no branch
                for i, task_in_done in enumerate(done_tasks_from_wait): # pragma: no cover
                    logger.debug(f"get_next_input_event: Processing done task #{i+1} (name: {task_in_done.get_name()})")
            
            for task in done_tasks_from_wait:
                queue_name = task.get_name()
                try:
                    event_result: Any = task.result() 
                    logger.debug(f"get_next_input_event: Task for queue '{queue_name}' completed. Result type: {type(event_result).__name__}, Result: {str(event_result)[:100]}")
                    
                    # Avoid circular import for BaseEvent, assuming it's correctly imported in TYPE_CHECKING context
                    from autobyteus.agent.events.agent_events import BaseEvent as AgentBaseEvent 
                    if isinstance(event_result, AgentBaseEvent):
                        event: 'BaseEvent' = event_result # type: ignore[type-var]
                        if event_tuple is None: 
                            event_tuple = (queue_name, event)
                            logger.debug(f"get_next_input_event: Dequeued event from {queue_name}: {type(event).__name__}")
                        else: # pragma: no cover
                            original_queue = next((q for n, q in self._input_queues if n == queue_name), None)
                            if original_queue:
                                original_queue.put_nowait(event) 
                                logger.warning(f"get_next_input_event: Re-queued event from {queue_name} (type {type(event).__name__}) as another event was processed first in the same wait cycle.")
                    else: # pragma: no cover
                        logger.error(f"get_next_input_event: Dequeued item from {queue_name} is not a BaseEvent subclass: {type(event_result)}. Event: {event_result!r}")

                except asyncio.CancelledError: # pragma: no cover
                     logger.info(f"get_next_input_event: Task for queue {queue_name} (from done set) was cancelled during result processing.")
                except Exception as e:  # pragma: no cover
                    logger.error(f"get_next_input_event: Error processing result from task for queue {queue_name} (from done set): {e}", exc_info=True)
            
            if pending_tasks_from_wait: # pragma: no branch
                logger.debug(f"get_next_input_event: Cancelling {len(pending_tasks_from_wait)} pending tasks from asyncio.wait.")
                for task_in_pending in pending_tasks_from_wait: # pragma: no cover
                    if not task_in_pending.done():
                        task_in_pending.cancel()
                        try:
                            await task_in_pending 
                        except asyncio.CancelledError:
                            pass 

        except asyncio.CancelledError: # pragma: no cover
            logger.debug("get_next_input_event: Coroutine itself was cancelled (e.g., by AgentRuntime timeout). All created tasks will be cancelled in finally.")
            raise 
        
        finally: # pragma: no branch
            logger.debug(f"get_next_input_event: Entering finally block. Cleaning up {len(created_tasks)} originally created tasks.")
            
            cleanup_awaits = []
            for task_to_clean in created_tasks: # pragma: no cover
                if not task_to_clean.done():
                    logger.debug(f"get_next_input_event (finally): Task '{task_to_clean.get_name()}' is not done, cancelling.")
                    task_to_clean.cancel()
                    cleanup_awaits.append(task_to_clean)
                else:
                    logger.debug(f"get_next_input_event (finally): Task '{task_to_clean.get_name()}' is already done.")

            if cleanup_awaits: # pragma: no cover
                logger.debug(f"get_next_input_event (finally): Awaiting {len(cleanup_awaits)} cancelled tasks.")
                results = await asyncio.gather(*cleanup_awaits, return_exceptions=True)
                for i, result in enumerate(results):
                    task_name_for_log = cleanup_awaits[i].get_name()
                    if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                        logger.warning(f"get_next_input_event (finally): Exception during cleanup of task '{task_name_for_log}': {result!r}")
                    elif isinstance(result, asyncio.CancelledError):
                         logger.debug(f"get_next_input_event (finally): Task '{task_name_for_log}' confirmed cancelled.")
            
            logger.debug(f"get_next_input_event: Finished finally block task cleanup.")

        if event_tuple:
            logger.debug(f"get_next_input_event: Returning event_tuple: {type(event_tuple[1]).__name__ if event_tuple else 'None'}")
        return event_tuple

    def log_remaining_items_at_shutdown(self): # pragma: no cover
        """Logs remaining items in input queues, typically called during shutdown."""
        logger.info("Logging remaining items in input queues at shutdown:")
        for name, q_obj in self._input_queues: 
            if q_obj is not None:
                q_size = q_obj.qsize()
                if q_size > 0:
                    logger.info(f"Input queue '{name}' has {q_size} items remaining at shutdown.")
