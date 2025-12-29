# file: autobyteus/autobyteus/agent/runtime/agent_worker.py
import asyncio
import logging
import traceback
import threading 
import concurrent.futures
from typing import TYPE_CHECKING, Optional, Any, Callable, Awaitable, List

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.events import ( 
    BaseEvent,
    AgentErrorEvent, 
    AgentStoppedEvent,
    AgentInputEventQueueManager,
    BootstrapStartedEvent,
    AgentEventStore,
)
from autobyteus.agent.events import WorkerEventDispatcher
from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager 
from autobyteus.agent.shutdown_steps import AgentShutdownOrchestrator
from autobyteus.agent.status.status_deriver import AgentStatusDeriver
from autobyteus.agent.status.status_update_utils import apply_event_and_derive_status

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.handlers import EventHandlerRegistry 

logger = logging.getLogger(__name__)

class AgentWorker:
    """
    Encapsulates the core event processing loop for an agent.
    It manages its own execution in a dedicated thread, runs its own asyncio event loop,
    and performs its own initialization sequence before processing external events.
    """

    def __init__(self,
                 context: 'AgentContext',
                 event_handler_registry: 'EventHandlerRegistry'): 
        self.context: 'AgentContext' = context
        
        self.status_manager = self.context.status_manager
        if not self.status_manager: # pragma: no cover
            raise ValueError(f"AgentWorker for '{self.context.agent_id}': AgentStatusManager not found.")

        self.worker_event_dispatcher = WorkerEventDispatcher(
            event_handler_registry=event_handler_registry
        )
        
        self._thread_pool_manager = AgentThreadPoolManager() 
        self._thread_future: Optional[concurrent.futures.Future] = None
        self._worker_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_stop_event: Optional[asyncio.Event] = None 
        
        self._is_active: bool = False 
        self._stop_initiated: bool = False 

        self._done_callbacks: list[Callable[[concurrent.futures.Future], None]] = []

        logger.info(f"AgentWorker initialized for agent_id '{self.context.agent_id}'.")

    async def _initialize(self) -> bool:
        """
        Runs the agent's initialization sequence via bootstrap events.
        Returns True on success, False on failure.
        """
        agent_id = self.context.agent_id
        logger.info(f"Agent '{agent_id}': Starting internal initialization process using bootstrap events.")

        await self.context.input_event_queues.enqueue_internal_system_event(BootstrapStartedEvent())

        while self.context.current_status not in [AgentStatus.IDLE, AgentStatus.ERROR]:
            if self._async_stop_event and self._async_stop_event.is_set():
                break
            try:
                queue_event_tuple = await asyncio.wait_for(
                    self.context.state.input_event_queues.get_next_internal_event(), timeout=0.1
                )
            except asyncio.TimeoutError:
                continue

            if queue_event_tuple is None:
                continue

            _queue_name, event_obj = queue_event_tuple
            await self.worker_event_dispatcher.dispatch(event_obj, self.context)
            await asyncio.sleep(0)

        return self.context.current_status == AgentStatus.IDLE

    async def _runtime_init(self) -> bool:
        """
        Initializes the minimal runtime prerequisites required for event handling.
        This must run before any event-driven bootstrap steps.
        """
        agent_id = self.context.agent_id
        if self.context.state.event_store is None:
            self.context.state.event_store = AgentEventStore(agent_id=agent_id)
            logger.info(f"Agent '{agent_id}': Runtime init completed (event store initialized).")

        if self.context.state.status_deriver is None:
            self.context.state.status_deriver = AgentStatusDeriver()
            logger.info(f"Agent '{agent_id}': Runtime init completed (status deriver initialized).")

        if self.context.state.input_event_queues is not None:
            logger.debug(f"Agent '{agent_id}': Runtime init skipped; input event queues already initialized.")
            return True

        try:
            queue_size = getattr(self.context.config, "input_event_queue_size", 0)
            if queue_size is None:
                queue_size = 0
            if queue_size < 0:
                logger.warning(
                    f"Agent '{agent_id}': input_event_queue_size must be >= 0. "
                    f"Got {queue_size}. Falling back to unbounded queues."
                )
                queue_size = 0

            self.context.state.input_event_queues = AgentInputEventQueueManager(queue_size=queue_size)
            logger.info(
                f"Agent '{agent_id}': Runtime init completed (input queues initialized, size={queue_size})."
            )
            return True
        except Exception as e:
            logger.critical(f"Agent '{agent_id}': Runtime init failed while initializing input queues: {e}", exc_info=True)
            return False

    def add_done_callback(self, callback: Callable[[concurrent.futures.Future], None]):
        """Adds a callback to be executed when the worker's thread completes."""
        if self._thread_future: 
            self._thread_future.add_done_callback(callback)
        else: 
            self._done_callbacks.append(callback)

    def get_worker_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Returns the worker's event loop if it's running."""
        return self._worker_loop if self._worker_loop and self._worker_loop.is_running() else None

    def schedule_coroutine_on_worker_loop(self, coro_factory: Callable[[], Awaitable[Any]]) -> concurrent.futures.Future:
        """Schedules a coroutine to be run on the worker's event loop from other threads."""
        worker_loop = self.get_worker_loop()
        if not worker_loop:
            raise RuntimeError(f"AgentWorker '{self.context.agent_id}': Worker event loop is not available.")
        return asyncio.run_coroutine_threadsafe(coro_factory(), worker_loop)

    def start(self) -> None:
        agent_id = self.context.agent_id
        if self._is_active or (self._thread_future and not self._thread_future.done()):
            logger.warning(f"AgentWorker '{agent_id}': Start called, but worker is already active or starting.")
            return

        logger.info(f"AgentWorker '{agent_id}': Starting...")
        self._is_active = True
        self._stop_initiated = False
        self._thread_future = self._thread_pool_manager.submit_task(self._run_managed_thread_loop)
        for cb in self._done_callbacks: 
            self._thread_future.add_done_callback(cb)
        self._done_callbacks.clear() 

    def _run_managed_thread_loop(self) -> None:
        thread_name = threading.current_thread().name
        agent_id = self.context.agent_id
        logger.info(f"AgentWorker '{agent_id}': Thread '{thread_name}' started. Setting up asyncio event loop.")
        
        try:
            self._worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._worker_loop)
            self._async_stop_event = asyncio.Event() 
            self._worker_loop.run_until_complete(self.async_run())
        except Exception as e:
            logger.error(f"AgentWorker '{agent_id}': Unhandled exception in _run_managed_thread_loop: {e}", exc_info=True)
            if not self.context.current_status.is_terminal():
                try:
                    self._apply_event_and_derive_status_sync(
                        AgentErrorEvent(
                            error_message=f"Worker thread fatal error: {e}",
                            exception_details=traceback.format_exc()
                        )
                    )
                except Exception as run_e:
                    logger.critical(f"AgentWorker '{agent_id}': Failed to emit derived error from sync context: {run_e}")
        finally:
            if self._worker_loop:
                try:
                    # Gather all remaining tasks and cancel them
                    tasks = asyncio.all_tasks(loop=self._worker_loop)
                    for task in tasks:
                        task.cancel()
                    
                    # Wait for all tasks to be cancelled
                    if tasks:
                        self._worker_loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                    
                    # Shutdown async generators
                    self._worker_loop.run_until_complete(self._worker_loop.shutdown_asyncgens())
                except Exception as cleanup_exc: # pragma: no cover
                    logger.error(f"AgentWorker '{agent_id}': Exception during event loop cleanup: {cleanup_exc}", exc_info=True)
                finally:
                    self._worker_loop.close()
            self._is_active = False

    async def async_run(self) -> None:
        agent_id = self.context.agent_id
        try:
            logger.info(f"AgentWorker '{agent_id}' async_run(): Starting.")
            
            # --- Direct Initialization ---
            runtime_init_successful = await self._runtime_init()
            if not runtime_init_successful:
                logger.critical(f"AgentWorker '{agent_id}' failed during runtime init. Worker is shutting down.")
                if self._async_stop_event and not self._async_stop_event.is_set():
                    self._async_stop_event.set()
                return

            initialization_successful = await self._initialize()
            if not initialization_successful:
                logger.critical(f"AgentWorker '{agent_id}' failed to initialize. Worker is shutting down.")
                if self._async_stop_event and not self._async_stop_event.is_set():
                    self._async_stop_event.set()
                return

            # --- Main Event Loop ---
            logger.info(f"AgentWorker '{agent_id}' initialized successfully. Entering main event loop.")
            while not self._async_stop_event.is_set(): 
                try:
                    if self.context.current_status == AgentStatus.BOOTSTRAPPING:
                        queue_event_tuple = await asyncio.wait_for(
                            self.context.state.input_event_queues.get_next_internal_event(), timeout=0.1
                        )
                    else:
                        queue_event_tuple = await asyncio.wait_for(
                            self.context.state.input_event_queues.get_next_input_event(), timeout=0.1
                        )
                except asyncio.TimeoutError:
                    if self._async_stop_event.is_set(): break
                    continue
                
                if queue_event_tuple is None:
                    if self._async_stop_event.is_set(): break
                    continue

                _queue_name, event_obj = queue_event_tuple
                await self.worker_event_dispatcher.dispatch(event_obj, self.context)
                await asyncio.sleep(0) 

        except asyncio.CancelledError:
            logger.info(f"AgentWorker '{agent_id}' async_run() loop task was cancelled.")
        except Exception as e:
            logger.error(f"Fatal error in AgentWorker '{agent_id}' async_run() loop: {e}", exc_info=True)
        finally:
            logger.info(f"AgentWorker '{agent_id}' async_run() loop has finished.")
            # --- Shutdown sequence moved here, inside the original task's finally block ---
            logger.info(f"AgentWorker '{agent_id}': Running shutdown sequence on worker loop.")
            orchestrator = AgentShutdownOrchestrator()
            cleanup_successful = await orchestrator.run(self.context)

            if not cleanup_successful:
                logger.critical(f"AgentWorker '{agent_id}': Shutdown resource cleanup failed. The agent may not have shut down cleanly.")
            else:
                logger.info(f"AgentWorker '{agent_id}': Shutdown resource cleanup completed successfully.")
            logger.info(f"AgentWorker '{agent_id}': Shutdown sequence completed.")


    async def stop(self, timeout: float = 10.0) -> None:
        """
        Gracefully stops the worker by signaling its event loop to terminate,
        then waiting for the thread to complete its cleanup and exit.
        """
        if not self._is_active or self._stop_initiated:
            return
        
        agent_id = self.context.agent_id
        logger.info(f"AgentWorker '{agent_id}': Stop requested.")
        self._stop_initiated = True

        # Schedule a coroutine on the worker's loop to set the stop event.
        if self.get_worker_loop():
            def _coro_factory():
                async def _signal_coro():
                    if self._async_stop_event and not self._async_stop_event.is_set():
                        self._async_stop_event.set()
                        if self.context.state.input_event_queues:
                            await self.context.state.input_event_queues.enqueue_internal_system_event(AgentStoppedEvent())
                return _signal_coro()
            
            future = self.schedule_coroutine_on_worker_loop(_coro_factory)
            try:
                # Wait for the signal to be processed.
                future.result(timeout=max(1.0, timeout-1))
            except Exception as e:
                logger.error(f"AgentWorker '{agent_id}': Error signaling stop event: {e}", exc_info=True)

        # Wait for the main thread future to complete.
        if self._thread_future:
            try:
                # FIX: Use asyncio.wait_for() to handle the timeout correctly.
                await asyncio.wait_for(asyncio.wrap_future(self._thread_future), timeout=timeout)
                logger.info(f"AgentWorker '{agent_id}': Worker thread has terminated.")
            except asyncio.TimeoutError:
                logger.warning(f"AgentWorker '{agent_id}': Timeout waiting for worker thread to terminate.")
        
        self._is_active = False

    def _apply_event_and_derive_status_sync(self, event: BaseEvent) -> None:
        try:
            asyncio.run(apply_event_and_derive_status(event, self.context))
        except Exception as e:  # pragma: no cover
            logger.error(f"AgentWorker '{self.context.agent_id}': Failed to project status: {e}", exc_info=True)


    def is_alive(self) -> bool:
        return self._thread_future is not None and not self._thread_future.done()
