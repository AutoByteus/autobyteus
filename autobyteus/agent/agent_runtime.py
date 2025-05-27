# file: autobyteus/autobyteus/agent/agent_runtime.py
import asyncio
import logging
import traceback 
from typing import Dict, Optional, Any, AsyncIterator, Type, cast

from autobyteus.agent.context import AgentContext 
from autobyteus.agent.events import END_OF_STREAM_SENTINEL, AgentEventQueues
from autobyteus.agent.context import AgentStatusManager 
from autobyteus.agent.events import (
    BaseEvent,
    AgentProcessingEvent, 
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
)
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.status import AgentStatus
# MODIFIED: Removed EventEmitter import as AgentRuntime will no longer inherit from it.
# from autobyteus.events.event_emitter import EventEmitter 
from autobyteus.events.event_types import EventType as ExternalEventType

logger = logging.getLogger(__name__)

class AgentRuntime: # MODIFIED: Removed EventEmitter inheritance
    """
    The active execution engine for an agent.
    Manages the agent's lifecycle, event loop, and dispatches events to handlers.
    Agent status management is delegated to an AgentStatusManager.
    It owns the AgentContext and EventHandlerRegistry.
    AgentRuntime itself no longer directly emits external events.
    """

    def __init__(self,
                 context: AgentContext, 
                 event_handler_registry: EventHandlerRegistry):
        
        # Initialize attributes
        self.context: AgentContext = context 
        self.event_handler_registry: EventHandlerRegistry = event_handler_registry
        
        self._main_loop_task: Optional[asyncio.Task] = None
        self._is_running_flag: bool = False 
        self._stop_requested: asyncio.Event = asyncio.Event()

        # MODIFIED: Removed super().__init__() call for EventEmitter
            
        self.status_manager: AgentStatusManager = AgentStatusManager(context) 
        
        logger.info(f"AgentRuntime initialized for agent_id '{self.context.agent_id}'. Definition: '{self.context.definition.name}'")
        registered_handlers_info = [cls.__name__ for cls in self.event_handler_registry.get_all_registered_event_types()]
        logger.debug(f"AgentRuntime '{self.context.agent_id}' configured with event_handler_registry for event types: {registered_handlers_info}")

    def start_execution_loop(self) -> None:
        if self.is_running: 
            logger.warning(f"AgentRuntime for '{self.context.agent_id}' is already running. Ignoring start request.")
            return

        self._is_running_flag = True 
        self._stop_requested.clear()
        
        self.status_manager.notify_runtime_starting()
            
        self._main_loop_task = asyncio.create_task(self._execution_loop(), name=f"agent_runtime_loop_{self.context.agent_id}")
        logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop task created.")

    async def _enqueue_fallback_sentinels(self):
        """Enqueues END_OF_STREAM_SENTINEL to all output queues as a fallback."""
        logger.debug(f"AgentRuntime '{self.context.agent_id}' enqueuing fallback sentinels to output queues.")
        queues_to_signal = [
            "assistant_output_chunk_queue",
            "assistant_final_message_queue",
            "tool_interaction_log_queue"
        ]
        for queue_name in queues_to_signal:
            try:
                await self.context.queues.enqueue_end_of_stream_sentinel_to_output_queue(queue_name)
            except Exception as e:
                logger.error(f"AgentRuntime '{self.context.agent_id}' failed to enqueue fallback sentinel to '{queue_name}': {e}", exc_info=True)


    async def stop_execution_loop(self, timeout: float = 10.0) -> None:
        if not self._is_running_flag and not self._main_loop_task : 
            logger.warning(f"AgentRuntime for '{self.context.agent_id}' is not running or already stopped. Ignoring stop request.")
            if self._is_running_flag: self._is_running_flag = False 
            return
        
        if self._stop_requested.is_set():
             logger.info(f"AgentRuntime for '{self.context.agent_id}' stop already in progress.")
             if self._main_loop_task and not self._main_loop_task.done():
                 try:
                     await asyncio.wait_for(self._main_loop_task, timeout=timeout)
                 except asyncio.TimeoutError:
                      logger.warning(f"AgentRuntime for '{self.context.agent_id}' timed out waiting for already stopping loop to complete.")
                 except asyncio.CancelledError:
                     pass 
             await self._enqueue_fallback_sentinels()
             await self.context.queues.graceful_shutdown(timeout=max(1.0, timeout / 2))
             await self.context.llm_instance.cleanup()
             self._is_running_flag = False
             self.status_manager.notify_final_shutdown_complete()
             return

        logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop stop requested (timeout: {timeout}s).")
        self._stop_requested.set() 

        await self.context.queues.enqueue_internal_system_event(AgentStoppedEvent())
        logger.debug(f"AgentRuntime '{self.context.agent_id}' enqueued AgentStoppedEvent for logging during shutdown request.")

        if self._main_loop_task and not self._main_loop_task.done():
            try:
                await asyncio.wait_for(self._main_loop_task, timeout=timeout)
                logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop stopped gracefully after processing remaining events.")
            except asyncio.TimeoutError:
                logger.warning(f"AgentRuntime for '{self.context.agent_id}' execution loop timed out during stop. Forcing cancellation.")
                self._main_loop_task.cancel()
                try:
                    await self._main_loop_task 
                except asyncio.CancelledError:
                    logger.info(f"AgentRuntime for '{self.context.agent_id}' execution loop task was cancelled.")
            except Exception as e: 
                logger.error(f"Exception during AgentRuntime '{self.context.agent_id}' stop's wait_for: {e}", exc_info=True)
                self.status_manager.notify_error_occurred() 

        await self._enqueue_fallback_sentinels()
        await self.context.queues.graceful_shutdown(timeout=max(1.0, timeout / 2)) 
        await self.context.llm_instance.cleanup() 
        
        self._is_running_flag = False 
        self._main_loop_task = None 

        self.status_manager.notify_final_shutdown_complete()
        
        logger.info(f"AgentRuntime for '{self.context.agent_id}' stop_execution_loop completed. Final status: {self.context.status.value}")


    async def _execution_loop(self) -> None:
        await self.context.queues.enqueue_internal_system_event(AgentStartedEvent())
        logger.info(f"Agent '{self.context.agent_id}' _execution_loop: Task starting, AgentStartedEvent enqueued.")

        try:
            while not self._stop_requested.is_set():
                logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Top of loop. Stop requested: {self._stop_requested.is_set()}. Current status: {self.context.status.value if self.context.status else 'None'}")
                try:
                    logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Attempting to get next event from queues.")
                    queue_event_tuple = await asyncio.wait_for(
                        self.context.queues.get_next_input_event(),
                        timeout=0.5 
                    )
                    logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: get_next_input_event returned: {type(queue_event_tuple[1]).__name__ if queue_event_tuple else 'None'}")
                except asyncio.TimeoutError:
                    logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Timed out waiting for event.")
                    if self.context.status == AgentStatus.RUNNING and \
                       all(q.empty() for _, q in self.context.queues._input_queues if q is not None): 
                         logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Agent is RUNNING and queues are empty, notifying for IDLE transition.")
                         self.status_manager.notify_processing_complete_queues_empty() 
                    continue 

                if queue_event_tuple is None: 
                    if self._stop_requested.is_set(): 
                        logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Stop requested and get_next_input_event returned None. Breaking loop.")
                        break
                    logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: get_next_input_event returned None, continuing loop.")
                    continue

                _queue_name, event_obj = queue_event_tuple
                
                if not isinstance(event_obj, BaseEvent): 
                    logger.warning(f"Agent '{self.context.agent_id}' _execution_loop: Received non-BaseEvent object from queue '{_queue_name}': {type(event_obj)}. Skipping.")
                    continue

                logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Event '{type(event_obj).__name__}' received from queue '{_queue_name}'. Current status: {self.context.status.value if self.context.status else 'None'}")
                if self.context.status == AgentStatus.IDLE and isinstance(event_obj, AgentProcessingEvent):
                    logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Agent is IDLE and received AgentProcessingEvent. Notifying for RUNNING transition.")
                    self.status_manager.notify_processing_event_dequeued()

                await self._dispatch_event(event_obj)
                
                if self.context.status == AgentStatus.RUNNING and \
                   isinstance(event_obj, AgentProcessingEvent) and \
                   all(q.empty() for _, q in self.context.queues._input_queues if q is not None): 
                     logger.debug(f"Agent '{self.context.agent_id}' _execution_loop: Processing of '{type(event_obj).__name__}' complete, agent is RUNNING and queues empty. Notifying for IDLE transition.")
                     self.status_manager.notify_processing_complete_queues_empty()


        except asyncio.CancelledError:
            logger.info(f"Agent '{self.context.agent_id}' _execution_loop was cancelled.")
        except Exception as e:
            logger.error(f"Fatal error in Agent '{self.context.agent_id}' _execution_loop: {e}", exc_info=True)
            self.status_manager.notify_error_occurred() 
            await self.context.queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=str(e), exception_details=traceback.format_exc())
            )
        finally:
            logger.info(f"Agent '{self.context.agent_id}' _execution_loop is exiting. Stop requested: {self._stop_requested.is_set()}")
            
            if not self._stop_requested.is_set() and self.context.status != AgentStatus.ERROR : 
                logger.warning(f"Agent '{self.context.agent_id}' _execution_loop ended unexpectedly. Notifying status manager.")
                self.status_manager.notify_runtime_stopping_or_loop_ended_unexpectedly() 
                await self.context.queues.enqueue_internal_system_event(AgentStoppedEvent())
            
            self._is_running_flag = False 
            logger.info(f"Agent '{self.context.agent_id}' _execution_loop has finished.")


    async def _dispatch_event(self, event: BaseEvent) -> None:
        event_class = type(event)
        handler = self.event_handler_registry.get_handler(event_class)

        if handler:
            event_class_name = event_class.__name__
            handler_class_name = type(handler).__name__
            
            if isinstance(event, AgentErrorEvent): 
                pass 
            elif isinstance(event, AgentStoppedEvent): 
                pass

            try:
                logger.debug(f"Agent '{self.context.agent_id}' _dispatch_event: Dispatching event type '{event_class_name}' to {handler_class_name}.")
                await handler.handle(event, self.context) 
                logger.debug(f"Agent '{self.context.agent_id}' _dispatch_event: Event '{event_class_name}' handled successfully by {handler_class_name}.")

                if isinstance(event, AgentStartedEvent):
                    self.status_manager.notify_agent_started_event_handled() 

            except Exception as e:
                error_msg = f"Agent '{self.context.agent_id}' _dispatch_event: Error handling event type '{event_class_name}' with {handler_class_name}: {e}"
                logger.error(error_msg, exc_info=True)
                self.status_manager.notify_error_occurred() 
                await self.context.queues.enqueue_internal_system_event(
                    AgentErrorEvent(error_message=error_msg, exception_details=traceback.format_exc())
                )
        else:
            logger.warning(f"Agent '{self.context.agent_id}' _dispatch_event: No handler registered for event type '{event_class.__name__}'. Event: {event}")


    @property
    def status(self) -> AgentStatus:
        # self.context should be initialized by now
        current_status = self.context.status
        if current_status is None: 
            logger.error(f"AgentRuntime '{self.context.agent_id}': context.status is None, which is unexpected. Defaulting to ERROR.")
            return AgentStatus.ERROR
        return current_status
        
    @property
    def is_running(self) -> bool:
        # self._is_running_flag and self._main_loop_task should be initialized
        return self._is_running_flag and \
               self._main_loop_task is not None and \
               not self._main_loop_task.done()

