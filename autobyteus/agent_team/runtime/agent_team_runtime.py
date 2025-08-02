# file: autobyteus/autobyteus/agent_team/runtime/agent_team_runtime.py
import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Optional

from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager
from autobyteus.agent_team.runtime.agent_team_worker import AgentTeamWorker
from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent
from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier
from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer

if TYPE_CHECKING:
    from autobyteus.agent_team.handlers.agent_team_event_handler_registry import AgentTeamEventHandlerRegistry

logger = logging.getLogger(__name__)

class AgentTeamRuntime:
    """The active execution engine for an agent team, managing the worker."""
    def __init__(self, context: AgentTeamContext, event_handler_registry: 'AgentTeamEventHandlerRegistry'):
        self.context = context
        self.notifier = AgentTeamExternalEventNotifier(team_id=self.context.team_id, runtime_ref=self)
        self.phase_manager = AgentTeamPhaseManager(context=self.context, notifier=self.notifier)
        
        # --- FIX: Set the phase_manager_ref on the context's state BEFORE creating the worker ---
        self.context.state.phase_manager_ref = self.phase_manager
        
        self._worker = AgentTeamWorker(self.context, event_handler_registry)
        
        self.multiplexer = AgentEventMultiplexer(
            team_id=self.context.team_id,
            notifier=self.notifier,
            worker_ref=self._worker
        )
        
        # Set other references on the context's state object for access by other components
        self.context.state.multiplexer_ref = self.multiplexer

        self._worker.add_done_callback(self._handle_worker_completion)
        logger.info(f"AgentTeamRuntime initialized for team '{self.context.team_id}'.")

    def get_worker_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Returns the worker's event loop if it's running."""
        return self._worker.get_worker_loop()

    def _handle_worker_completion(self, future: asyncio.Future):
        team_id = self.context.team_id
        try:
            future.result()
            logger.info(f"AgentTeamRuntime '{team_id}': Worker thread completed.")
        except Exception as e:
            logger.error(f"AgentTeamRuntime '{team_id}': Worker thread terminated with exception: {e}", exc_info=True)
        if not self.context.state.current_phase.is_terminal():
             asyncio.run(self.phase_manager.notify_final_shutdown_complete())
        
    def start(self):
        if self._worker.is_alive:
            return
        self._worker.start()

    async def stop(self, timeout: float = 10.0):
        await self.phase_manager.notify_shutdown_initiated()
        await self._worker.stop(timeout=timeout)
        await self.phase_manager.notify_final_shutdown_complete()

    async def submit_event(self, event: BaseAgentTeamEvent):
        if not self._worker.is_alive:
            raise RuntimeError("Agent team worker is not active.")
        def _coro_factory():
            async def _enqueue():
                from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent
                if isinstance(event, ProcessUserMessageEvent):
                    await self.context.state.input_event_queues.enqueue_user_message(event)
                else:
                    await self.context.state.input_event_queues.enqueue_internal_system_event(event)
            return _enqueue()
        future = self._worker.schedule_coroutine(_coro_factory)
        await asyncio.wrap_future(future)

    @property
    def is_running(self) -> bool:
        return self._worker.is_alive
