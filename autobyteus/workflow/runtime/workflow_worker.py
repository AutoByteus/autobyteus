# file: autobyteus/autobyteus/workflow/runtime/workflow_worker.py
import asyncio
import logging
import concurrent.futures
from typing import TYPE_CHECKING, Optional, Callable, Awaitable, Any

from autobyteus.workflow.events.workflow_event_dispatcher import WorkflowEventDispatcher
from autobyteus.workflow.bootstrap_steps.workflow_bootstrapper import WorkflowBootstrapper
from autobyteus.workflow.shutdown_steps.workflow_shutdown_orchestrator import WorkflowShutdownOrchestrator
from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.handlers.workflow_event_handler_registry import WorkflowEventHandlerRegistry

logger = logging.getLogger(__name__)

class WorkflowWorker:
    """Encapsulates the core event processing loop for a workflow."""
    def __init__(self, context: 'WorkflowContext', event_handler_registry: 'WorkflowEventHandlerRegistry'):
        self.context = context
        self.phase_manager = self.context.phase_manager
        self.event_dispatcher = WorkflowEventDispatcher(event_handler_registry, self.phase_manager)
        
        self._thread_pool_manager = AgentThreadPoolManager()
        self._thread_future: Optional[concurrent.futures.Future] = None
        self._worker_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_stop_event: Optional[asyncio.Event] = None
        self._is_active: bool = False
        self._stop_initiated: bool = False
        self._done_callbacks: list[Callable[[concurrent.futures.Future], None]] = []
        logger.info(f"WorkflowWorker initialized for workflow '{self.context.workflow_id}'.")

    def get_worker_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Returns the worker's event loop if it's running."""
        return self._worker_loop if self._worker_loop and self._worker_loop.is_running() else None

    def add_done_callback(self, callback: Callable):
        if self._thread_future:
            self._thread_future.add_done_callback(callback)
        else:
            self._done_callbacks.append(callback)

    def schedule_coroutine(self, coro_factory: Callable[[], Awaitable[Any]]) -> concurrent.futures.Future:
        if not self._worker_loop:
            raise RuntimeError("WorkflowWorker loop is not available.")
        return asyncio.run_coroutine_threadsafe(coro_factory(), self._worker_loop)

    def start(self):
        if self._is_active:
            return
        self._is_active = True
        self._thread_future = self._thread_pool_manager.submit_task(self._run_managed_loop)
        for cb in self._done_callbacks:
            self._thread_future.add_done_callback(cb)
        self._done_callbacks.clear()

    def _run_managed_loop(self):
        try:
            self._worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._worker_loop)
            self._async_stop_event = asyncio.Event()
            self._worker_loop.run_until_complete(self.async_run())
        except Exception as e:
            logger.error(f"WorkflowWorker '{self.context.workflow_id}' event loop crashed: {e}", exc_info=True)
        finally:
            if self._worker_loop:
                self._worker_loop.close()
            self._is_active = False

    async def async_run(self):
        bootstrapper = WorkflowBootstrapper()
        if not await bootstrapper.run(self.context, self.phase_manager):
            logger.critical(f"Workflow '{self.context.workflow_id}' failed to initialize. Shutting down.")
            return

        logger.info(f"Workflow '{self.context.workflow_id}' entering main event loop.")
        while not self._async_stop_event.is_set():
            try:
                # Combine queues for a single wait point
                user_message_task = asyncio.create_task(self.context.state.input_event_queues.user_message_queue.get())
                system_task = asyncio.create_task(self.context.state.input_event_queues.internal_system_event_queue.get())
                done, pending = await asyncio.wait([user_message_task, system_task], return_when=asyncio.FIRST_COMPLETED, timeout=0.2)
                
                for task in pending:
                    task.cancel()
                
                if not done:
                    continue

                event = done.pop().result()
                await self.event_dispatcher.dispatch(event, self.context)

            except asyncio.TimeoutError:
                continue
        
        logger.info(f"Workflow '{self.context.workflow_id}' shutdown signal received. Cleaning up.")
        shutdown_orchestrator = WorkflowShutdownOrchestrator()
        await shutdown_orchestrator.run(self.context)

    async def stop(self, timeout: float = 10.0):
        if not self._is_active or self._stop_initiated:
            return
        self._stop_initiated = True
        if self._worker_loop:
            self._worker_loop.call_soon_threadsafe(self._async_stop_event.set)
        if self._thread_future:
            try:
                # FIX: Use asyncio.wait_for() to handle the timeout correctly.
                await asyncio.wait_for(asyncio.wrap_future(self._thread_future), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for workflow worker '{self.context.workflow_id}' to terminate.")
        self._is_active = False

    @property
    def is_alive(self) -> bool:
        return self._thread_future is not None and not self._thread_future.done()
