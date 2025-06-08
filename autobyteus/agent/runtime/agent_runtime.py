# file: autobyteus/autobyteus/agent/runtime/agent_runtime.py
import asyncio
import logging
import traceback 
import threading 
import concurrent.futures 
from typing import Dict, Optional, Any, Callable, Awaitable, TYPE_CHECKING 

from autobyteus.agent.context.agent_context import AgentContext 
from autobyteus.agent.context.phases import AgentOperationalPhase 
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 
from autobyteus.agent.events.agent_events import ( 
    BaseEvent,
    BootstrapAgentEvent,
    UserMessageReceivedEvent,
    InterAgentMessageReceivedEvent,
    ToolExecutionApprovalEvent,
)

from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager 
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.runtime.agent_worker import AgentWorker


logger = logging.getLogger(__name__)

class AgentRuntime:
    """
    The active execution engine for an agent.
    Manages the agent's lifecycle. It creates an AgentWorker instance,
    which then manages its own thread and asyncio event loop.
    AgentRuntime interacts with AgentWorker via its public start/stop API
    and by submitting events for processing by the worker.
    """

    def __init__(self,
                 context: AgentContext, 
                 event_handler_registry: EventHandlerRegistry):
        
        if not isinstance(context, AgentContext): 
            raise TypeError(f"AgentRuntime requires a composite AgentContext instance. Got {type(context)}")
        if not isinstance(event_handler_registry, EventHandlerRegistry):
            raise TypeError(f"AgentRuntime requires an EventHandlerRegistry instance. Got {type(event_handler_registry)}")

        self.context: AgentContext = context 
        self.event_handler_registry: EventHandlerRegistry = event_handler_registry
        
        # --- CORRECTED INITIALIZATION ORDER ---
        # 1. Create the notifier and phase manager.
        self.external_event_notifier: AgentExternalEventNotifier = AgentExternalEventNotifier(agent_id=self.context.agent_id)
        self.phase_manager: AgentPhaseManager = AgentPhaseManager(context=self.context, notifier=self.external_event_notifier) 
        
        # 2. Assign the phase manager to the context's state. This is critical.
        self.context.state.phase_manager_ref = self.phase_manager 
        logger.debug(f"AgentRuntime '{self.context.agent_id}': phase_manager_ref set on context.state.")
        
        # 3. Now, create the worker, which depends on the phase manager being in the context.
        self._worker: AgentWorker = AgentWorker(
            context=self.context,
            event_handler_registry=self.event_handler_registry
        )
        self._worker.add_done_callback(self._handle_worker_completion)

        self._bootstrap_event_enqueued = False 

        logger.info(f"AgentRuntime initialized for agent_id '{self.context.agent_id}'. AgentWorker created.")

    def get_worker_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Returns the event loop of the agent's worker, if active."""
        if self._worker and self._worker.is_alive(): # pragma: no branch
            return self._worker.get_worker_loop()
        return None # pragma: no cover

    def _schedule_coroutine_on_worker(self, coro_factory: Callable[[], Awaitable[Any]]) -> concurrent.futures.Future:
        """
        Schedules a coroutine (created by coro_factory) on the worker's event loop.
        """
        worker_loop = self._worker.get_worker_loop()
        if not worker_loop : # pragma: no cover
             logger.error(f"AgentRuntime '{self.context.agent_id}': Worker loop not available for _schedule_coroutine_on_worker.")
             f = concurrent.futures.Future()
             f.set_exception(RuntimeError(f"AgentRuntime '{self.context.agent_id}': Worker loop not available."))
             return f
        return self._worker.schedule_coroutine_on_worker_loop(coro_factory)


    async def submit_event(self, event: BaseEvent) -> None: 
        """
        Submits an event to the agent's runtime for processing by the worker.
        """
        agent_id = self.context.agent_id
        if not self._worker or not self._worker.is_alive(): # pragma: no cover
            logger.error(f"AgentRuntime '{agent_id}': Worker not active. Cannot submit event {type(event).__name__}.")
            raise RuntimeError(f"Agent '{agent_id}' worker is not active.")

        def _coro_factory() -> Awaitable[Any]:
            async def _enqueue_coro():
                if not self.context.state.input_event_queues: # pragma: no cover
                    logger.critical(f"AgentRuntime '{agent_id}': CRITICAL! Input event queues not initialized in worker loop when trying to enqueue {type(event).__name__}. Bootstrap failure.")
                    return 
                
                logger.debug(f"AgentRuntime '{agent_id}' (worker loop): Preparing to enqueue {type(event).__name__}.")
                try:
                    if isinstance(event, UserMessageReceivedEvent):
                        await self.context.state.input_event_queues.enqueue_user_message(event)
                    elif isinstance(event, InterAgentMessageReceivedEvent):
                        await self.context.state.input_event_queues.enqueue_inter_agent_message(event)
                    elif isinstance(event, ToolExecutionApprovalEvent):
                        await self.context.state.input_event_queues.enqueue_tool_approval_event(event)
                    else: 
                        await self.context.state.input_event_queues.enqueue_internal_system_event(event)
                    logger.debug(f"AgentRuntime '{agent_id}' (worker loop): Successfully enqueued {type(event).__name__}.")
                except Exception as e: # pragma: no cover
                    logger.error(f"AgentRuntime '{agent_id}' (worker loop): Error during event enqueue for {type(event).__name__}: {e}", exc_info=True)
            return _enqueue_coro()

        logger.debug(f"AgentRuntime '{agent_id}': Submitting {type(event).__name__} to worker.")
        future = self._schedule_coroutine_on_worker(_coro_factory)
        
        try:
            await asyncio.wait_for(asyncio.wrap_future(future), timeout=1.0) 
            logger.debug(f"AgentRuntime '{agent_id}': {type(event).__name__} successfully submitted to worker.")
        except asyncio.TimeoutError: # pragma: no cover
            logger.warning(f"AgentRuntime '{agent_id}': Timeout occurred while waiting for {type(event).__name__} to be submitted to worker. Event might still be processed if queue is busy.")
        except Exception as e: # pragma: no cover
            if isinstance(e, RuntimeError) and "Worker loop not available" in str(e):
                 raise 
            logger.error(f"AgentRuntime '{agent_id}': Error while waiting for submission of {type(event).__name__} to worker: {e}", exc_info=True)
            raise RuntimeError(f"Failed to submit event to agent '{agent_id}' worker: {e}")


    def start(self) -> None: 
        agent_id = self.context.agent_id
        if self._worker.is_alive(): 
            logger.warning(f"AgentRuntime for '{agent_id}' is already running (worker is alive). Ignoring start request.")
            return
        
        logger.info(f"AgentRuntime for '{agent_id}': Starting worker.")
        self.phase_manager.notify_runtime_starting_and_uninitialized()
        self._bootstrap_event_enqueued = False 
        self._worker.start() 
        logger.info(f"AgentRuntime for '{agent_id}': Worker start command issued.")

        async def _init_bootstrap():
            logger.debug(f"AgentRuntime '{agent_id}': _init_bootstrap started, waiting for worker loop.")
            worker_loop = None
            timeout_seconds = 5.0 
            start_time = asyncio.get_event_loop().time()

            while not worker_loop:
                if not self._worker.is_alive(): # pragma: no cover
                    logger.error(f"AgentRuntime '{agent_id}': Worker died before its loop became available. Bootstrap aborted.")
                    self.phase_manager.notify_error_occurred(
                        "WorkerPrematureExit",
                        "Agent worker's thread exited before its event loop was ready for bootstrap."
                    )
                    return
                
                worker_loop = self._worker.get_worker_loop()
                if worker_loop:
                    break
                
                if (asyncio.get_event_loop().time() - start_time) > timeout_seconds: # pragma: no cover
                    logger.error(f"AgentRuntime '{agent_id}': Worker loop did not become available in {timeout_seconds}s for bootstrap. Bootstrap aborted.")
                    self.phase_manager.notify_error_occurred(
                        "WorkerInitializationTimeout", 
                        "Agent worker's event loop did not become available within the timeout period."
                    )
                    return
                await asyncio.sleep(0.01) 
            
            logger.info(f"AgentRuntime '{agent_id}': Worker loop is active. Submitting BootstrapAgentEvent.")
            try:
                await self.submit_event(BootstrapAgentEvent()) 
                self._bootstrap_event_enqueued = True
                logger.info(f"AgentRuntime '{agent_id}': BootstrapAgentEvent successfully submitted.")
            except Exception as e: # pragma: no cover
                logger.critical(f"AgentRuntime '{agent_id}': CRITICAL - Failed to submit BootstrapAgentEvent: {e}", exc_info=True)
                self.phase_manager.notify_error_occurred(
                    "BootstrapSubmissionFailure", 
                    f"Failed to submit initial BootstrapAgentEvent to worker: {e}"
                )
        try:
            asyncio.create_task(_init_bootstrap())
        except RuntimeError as e: # pragma: no cover
             logger.error(f"AgentRuntime '{agent_id}': Failed to create task for _init_bootstrap. Ensure AgentRuntime.start() is called from an async context with a running event loop. Error: {e}")

    def _handle_worker_completion(self, future: concurrent.futures.Future) -> None: # pragma: no cover
        thread_name = threading.current_thread().name 
        agent_id = self.context.agent_id
        logger.info(f"AgentRuntime '{agent_id}': Worker completion callback (_handle_worker_completion) executing in thread '{thread_name}'.")
        
        worker_exited_unexpectedly = False
        exception_details = "No specific exception details from future."
        try:
            future.result() 
            logger.info(f"AgentRuntime '{agent_id}': Worker thread completed successfully (as per future result).")
        except asyncio.CancelledError: 
            logger.info(f"AgentRuntime '{agent_id}': Worker thread future was cancelled.")
            worker_exited_unexpectedly = True 
            exception_details = "Worker thread future was cancelled."
        except Exception as e:
            logger.error(f"AgentRuntime '{agent_id}': Worker thread terminated with an exception: {e}", exc_info=True)
            worker_exited_unexpectedly = True
            try: 
                exc = future.exception(timeout=0)
                if exc: exception_details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            except Exception: pass 

        if worker_exited_unexpectedly or (self._worker and not self._worker._stop_initiated):
            logger.error(f"AgentRuntime '{agent_id}': Worker thread exited unexpectedly or without explicit stop. Current phase: {self.context.current_phase.value if self.context.current_phase else 'N/A'}")
            if self.phase_manager and self.context.current_phase and not self.context.current_phase.is_terminal():
                self.phase_manager.notify_error_occurred("Worker thread exited unexpectedly.", exception_details)
        
        if self.phase_manager and self.context.current_phase and not self.context.current_phase.is_terminal():
             logger.info(f"AgentRuntime '{agent_id}': Worker completed, current phase {self.context.current_phase.value} is not terminal. Notifying final shutdown.")
             self.phase_manager.notify_final_shutdown_complete()
        
        logger.debug(f"AgentRuntime '{agent_id}': Worker completion callback finished.")
        
    async def stop(self, timeout: float = 10.0) -> None: # pragma: no cover
        agent_id = self.context.agent_id
        if not self._worker.is_alive() and not self._worker._is_active : 
            logger.warning(f"AgentRuntime for '{agent_id}' is already stopped or was never fully started. Ignoring stop request.")
            if self.phase_manager and self.context.current_phase and not self.context.current_phase.is_terminal():
                self.phase_manager.notify_final_shutdown_complete()
            return
        
        logger.info(f"AgentRuntime for '{agent_id}': Stopping (timeout: {timeout}s).")
        if self.phase_manager: self.phase_manager.notify_shutdown_initiated() 

        await self._worker.stop(timeout=timeout) 

        logger.debug(f"AgentRuntime '{agent_id}': Worker stop completed. Proceeding with AgentRuntime cleanup.")
        # REMOVED: Graceful shutdown call for output_data_queues as they no longer exist here.
        # if self.context.state.output_data_queues: 
        #     await self.context.state.output_data_queues.graceful_shutdown(timeout=max(1.0, timeout / 2)) 
        
        if self.context.llm_instance and hasattr(self.context.llm_instance, 'cleanup'): 
            if asyncio.iscoroutinefunction(self.context.llm_instance.cleanup):
                 try: await self.context.llm_instance.cleanup()
                 except RuntimeError as e_cleanup_loop: 
                     logger.warning(f"Could not await LLM cleanup for '{agent_id}': {e_cleanup_loop}")
            else:
                 self.context.llm_instance.cleanup()
        
        if self.phase_manager: self.phase_manager.notify_final_shutdown_complete() 
        logger.info(f"AgentRuntime for '{agent_id}' stop() method completed. Final phase: {self.context.current_phase.value if self.context.current_phase else 'N/A'}")

    @property 
    def current_phase_property(self) -> AgentOperationalPhase: 
        return self.context.current_phase 
        
    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()
