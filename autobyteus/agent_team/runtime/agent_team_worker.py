# file: autobyteus/autobyteus/agent_team/runtime/agent_team_worker.py
import asyncio
import logging
import concurrent.futures
from typing import TYPE_CHECKING, Optional, Callable, Awaitable, Any

from autobyteus.agent_team.events.agent_team_event_dispatcher import AgentTeamEventDispatcher
from autobyteus.agent_team.events.agent_team_events import (
    AgentTeamBootstrapStartedEvent,
    AgentTeamReadyEvent,
    AgentTeamErrorEvent,
    AgentTeamStoppedEvent,
)
from autobyteus.agent_team.events.agent_team_input_event_queue_manager import AgentTeamInputEventQueueManager
from autobyteus.agent_team.events.event_store import AgentTeamEventStore
from autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper import AgentTeamBootstrapper
from autobyteus.agent_team.shutdown_steps.agent_team_shutdown_orchestrator import AgentTeamShutdownOrchestrator
from autobyteus.agent_team.status.status_deriver import AgentTeamStatusDeriver
from autobyteus.agent_team.status.status_update_utils import apply_event_and_derive_status
from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.handlers.agent_team_event_handler_registry import AgentTeamEventHandlerRegistry

logger = logging.getLogger(__name__)

class AgentTeamWorker:
    """Encapsulates the core event processing loop for an agent team."""
    def __init__(self, context: 'AgentTeamContext', event_handler_registry: 'AgentTeamEventHandlerRegistry'):
        self.context = context
        self.status_manager = self.context.status_manager
        if not self.status_manager:  # pragma: no cover
            raise ValueError(f"AgentTeamWorker for '{self.context.team_id}': AgentTeamStatusManager not found.")

        self.event_dispatcher = AgentTeamEventDispatcher(event_handler_registry)
        
        self._thread_pool_manager = AgentThreadPoolManager()
        self._thread_future: Optional[concurrent.futures.Future] = None
        self._worker_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_stop_event: Optional[asyncio.Event] = None
        self._is_active: bool = False
        self._stop_initiated: bool = False
        self._done_callbacks: list[Callable[[concurrent.futures.Future], None]] = []
        logger.info(f"AgentTeamWorker initialized for team '{self.context.team_id}'.")

    async def _runtime_init(self) -> bool:
        team_id = self.context.team_id
        if self.context.state.event_store is None:
            self.context.state.event_store = AgentTeamEventStore(team_id=team_id)
            logger.info(f"Team '{team_id}': Runtime init completed (event store initialized).")

        if self.context.state.status_deriver is None:
            self.context.state.status_deriver = AgentTeamStatusDeriver()
            logger.info(f"Team '{team_id}': Runtime init completed (status deriver initialized).")

        if self.context.state.input_event_queues is not None:
            logger.debug(f"Team '{team_id}': Runtime init skipped; input event queues already initialized.")
            return True

        try:
            self.context.state.input_event_queues = AgentTeamInputEventQueueManager()
            logger.info(f"Team '{team_id}': Runtime init completed (input queues initialized).")
            return True
        except Exception as e:
            logger.critical(f"Team '{team_id}': Runtime init failed while initializing input queues: {e}", exc_info=True)
            return False

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
            raise RuntimeError("AgentTeamWorker loop is not available.")
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
            logger.error(f"AgentTeamWorker '{self.context.team_id}' event loop crashed: {e}", exc_info=True)
        finally:
            if self._worker_loop:
                self._worker_loop.close()
            self._is_active = False

    async def async_run(self):
        team_id = self.context.team_id
        if not await self._runtime_init():
            logger.critical(f"Team '{team_id}': Runtime init failed. Shutting down.")
            await apply_event_and_derive_status(
                AgentTeamErrorEvent(error_message="Runtime init failed.", exception_details="Failed to initialize event store or queues."),
                self.context
            )
            return

        bootstrapper = AgentTeamBootstrapper()
        await self.event_dispatcher.dispatch(AgentTeamBootstrapStartedEvent(), self.context)
        if not await bootstrapper.run(self.context):
            logger.critical(f"Team '{team_id}' failed to initialize. Shutting down.")
            await self.event_dispatcher.dispatch(
                AgentTeamErrorEvent(error_message="Bootstrap failed.", exception_details="Bootstrapper returned failure."),
                self.context
            )
            return

        await self.event_dispatcher.dispatch(AgentTeamReadyEvent(), self.context)

        logger.info(f"Team '{self.context.team_id}' entering main event loop.")
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
        
        logger.info(f"Team '{self.context.team_id}' shutdown signal received. Cleaning up.")
        shutdown_orchestrator = AgentTeamShutdownOrchestrator()
        await shutdown_orchestrator.run(self.context)

    async def stop(self, timeout: float = 10.0):
        if not self._is_active or self._stop_initiated:
            return
        self._stop_initiated = True
        if self._worker_loop:
            def _coro_factory():
                async def _signal_coro():
                    if self._async_stop_event and not self._async_stop_event.is_set():
                        self._async_stop_event.set()
                        if self.context.state.input_event_queues:
                            await self.context.state.input_event_queues.enqueue_internal_system_event(
                                AgentTeamStoppedEvent()
                            )
                return _signal_coro()
            try:
                future = self.schedule_coroutine(_coro_factory)
                future.result(timeout=max(1.0, timeout - 1))
            except Exception as e:
                logger.error(f"Team '{self.context.team_id}': Error signaling stop event: {e}", exc_info=True)
        if self._thread_future:
            try:
                # FIX: Use asyncio.wait_for() to handle the timeout correctly.
                await asyncio.wait_for(asyncio.wrap_future(self._thread_future), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for team worker '{self.context.team_id}' to terminate.")
        self._is_active = False

    @property
    def is_alive(self) -> bool:
        return self._thread_future is not None and not self._thread_future.done()
