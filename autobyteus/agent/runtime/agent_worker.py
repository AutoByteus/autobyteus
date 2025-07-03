# file: autobyteus/autobyteus/agent/runtime/agent_worker.py
import asyncio
import logging
import traceback
import threading 
import concurrent.futures
from typing import TYPE_CHECKING, Optional, Any, Callable, Awaitable, List

from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.agent.events import ( 
    BaseEvent,
    AgentErrorEvent, 
    AgentStoppedEvent,
)
from autobyteus.agent.events import WorkerEventDispatcher
from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager 
from autobyteus.agent.bootstrap_steps.agent_bootstrapper import AgentBootstrapper

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
        
        self.phase_manager = self.context.phase_manager
        if not self.phase_manager: # pragma: no cover
            raise ValueError(f"AgentWorker for '{self.context.agent_id}': AgentPhaseManager not found.")

        self.worker_event_dispatcher = WorkerEventDispatcher(
            event_handler_registry=event_handler_registry, 
            phase_manager=self.phase_manager
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
        Runs the agent's initialization sequence by using an AgentBootstrapper.
        Returns True on success, False on failure.
        """
        agent_id = self.context.agent_id
        logger.info(f"Agent '{agent_id}': Starting internal initialization process using AgentBootstrapper.")

        bootstrapper = AgentBootstrapper() # Using default steps
        initialization_successful = await bootstrapper.run(self.context, self.phase_manager)

        return initialization_successful

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
            if self.phase_manager and not self.context.current_phase.is_terminal():
                try:
                    # Since this is a sync context, we must run the async phase manager method in a temporary event loop.
                    asyncio.run(self.phase_manager.notify_error_occurred(f"Worker thread fatal error: {e}", traceback.format_exc()))
                except Exception as run_e:
                    logger.critical(f"AgentWorker '{agent_id}': Failed to run async error notification from sync context: {run_e}")
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
        logger.info(f"AgentWorker '{agent_id}' async_run(): Starting.")
        
        # --- Direct Initialization ---
        initialization_successful = await self._initialize()
        if not initialization_successful:
            logger.critical(f"AgentWorker '{agent_id}' failed to initialize. Worker is shutting down.")
            if self._async_stop_event and not self._async_stop_event.is_set():
                self._async_stop_event.set()
            return
        
        # --- Main Event Loop ---
        logger.info(f"AgentWorker '{agent_id}' initialized successfully. Entering main event loop.")
        try:
            while not self._async_stop_event.is_set(): 
                try:
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

    async def _signal_internal_stop(self):
        if self._async_stop_event and not self._async_stop_event.is_set():
            self._async_stop_event.set()
            if self.context.state.input_event_queues:
                await self.context.state.input_event_queues.enqueue_internal_system_event(AgentStoppedEvent())

    async def stop(self, timeout: float = 10.0) -> None:
        if not self._is_active or self._stop_initiated:
            return
        self._stop_initiated = True
        if self.get_worker_loop() and self._async_stop_event:
            future = asyncio.run_coroutine_threadsafe(self._signal_internal_stop(), self.get_worker_loop())
            try: future.result(timeout=1.0)
            except Exception: pass
        if self._thread_future:
            try: await asyncio.wait_for(asyncio.wrap_future(self._thread_future), timeout=timeout)
            except asyncio.TimeoutError: logger.warning(f"Timeout waiting for worker thread of '{self.context.agent_id}'.")
        self._is_active = False

    def is_alive(self) -> bool:
        return self._thread_future is not None and not self._thread_future.done()
