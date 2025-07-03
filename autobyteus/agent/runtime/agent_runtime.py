# file: autobyteus/autobyteus/agent/runtime/agent_runtime.py
import asyncio
import logging
import traceback 
import concurrent.futures 
from typing import Optional, Any, Callable, Awaitable, TYPE_CHECKING 

from autobyteus.agent.context import AgentContext 
from autobyteus.agent.phases import AgentOperationalPhase, AgentPhaseManager 
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 
from autobyteus.agent.events import BaseEvent
from autobyteus.agent.handlers import EventHandlerRegistry
from autobyteus.agent.runtime.agent_worker import AgentWorker

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

class AgentRuntime:
    """
    The active execution engine for an agent. It creates and manages an AgentWorker.
    """

    def __init__(self,
                 context: AgentContext, 
                 event_handler_registry: EventHandlerRegistry):
        
        self.context: AgentContext = context 
        self.event_handler_registry: EventHandlerRegistry = event_handler_registry
        
        self.external_event_notifier: AgentExternalEventNotifier = AgentExternalEventNotifier(agent_id=self.context.agent_id)
        self.phase_manager: AgentPhaseManager = AgentPhaseManager(context=self.context, notifier=self.external_event_notifier) 
        
        self.context.state.phase_manager_ref = self.phase_manager 
        
        self._worker: AgentWorker = AgentWorker(
            context=self.context,
            event_handler_registry=self.event_handler_registry,
        )
        self._worker.add_done_callback(self._handle_worker_completion)

        logger.info(f"AgentRuntime initialized for agent_id '{self.context.agent_id}'.")

    def get_worker_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return self._worker.get_worker_loop()

    def _schedule_coroutine_on_worker(self, coro_factory: Callable[[], Awaitable[Any]]) -> concurrent.futures.Future:
        worker_loop = self._worker.get_worker_loop()
        if not worker_loop:
             raise RuntimeError(f"AgentRuntime '{self.context.agent_id}': Worker loop not available.")
        return self._worker.schedule_coroutine_on_worker_loop(coro_factory)

    async def submit_event(self, event: BaseEvent) -> None: 
        from autobyteus.agent.events import UserMessageReceivedEvent, InterAgentMessageReceivedEvent, ToolExecutionApprovalEvent

        agent_id = self.context.agent_id
        if not self._worker or not self._worker.is_alive():
            raise RuntimeError(f"Agent '{agent_id}' worker is not active.")

        def _coro_factory() -> Awaitable[Any]:
            async def _enqueue_coro():
                if not self.context.state.input_event_queues:
                    logger.critical(f"AgentRuntime '{agent_id}': Input event queues not initialized for event {type(event).__name__}.")
                    return 
                
                if isinstance(event, UserMessageReceivedEvent):
                    await self.context.state.input_event_queues.enqueue_user_message(event)
                elif isinstance(event, InterAgentMessageReceivedEvent):
                    await self.context.state.input_event_queues.enqueue_inter_agent_message(event)
                elif isinstance(event, ToolExecutionApprovalEvent):
                    await self.context.state.input_event_queues.enqueue_tool_approval_event(event)
                else: 
                    await self.context.state.input_event_queues.enqueue_internal_system_event(event)
            return _enqueue_coro()

        future = self._schedule_coroutine_on_worker(_coro_factory)
        await asyncio.wrap_future(future)

    def start(self) -> None: 
        agent_id = self.context.agent_id
        if self._worker.is_alive(): 
            logger.warning(f"AgentRuntime for '{agent_id}' is already running. Ignoring start request.")
            return
        
        logger.info(f"AgentRuntime for '{agent_id}': Starting worker.")
        # The first meaningful phase change to BOOTSTRAPPING is triggered by the AgentBootstrapper
        # within the worker's async context.
        self._worker.start() 
        logger.info(f"AgentRuntime for '{agent_id}': Worker start command issued. Worker will initialize itself.")

    def _handle_worker_completion(self, future: concurrent.futures.Future):
        agent_id = self.context.agent_id
        try:
            future.result() 
            logger.info(f"AgentRuntime '{agent_id}': Worker thread completed successfully.")
        except Exception as e:
            logger.error(f"AgentRuntime '{agent_id}': Worker thread terminated with an exception: {e}", exc_info=True)
            if not self.context.current_phase.is_terminal():
                # Since the phase manager is now async, we must run it in a new event loop.
                try:
                    asyncio.run(self.phase_manager.notify_error_occurred("Worker thread exited unexpectedly.", traceback.format_exc()))
                except Exception as run_e:
                    logger.critical(f"AgentRuntime '{agent_id}': Failed to run async error notification: {run_e}")
        
        if not self.context.current_phase.is_terminal():
             # Use asyncio.run() to execute the final async phase transition from a sync callback.
             try:
                 asyncio.run(self.phase_manager.notify_final_shutdown_complete())
             except Exception as run_e:
                 logger.critical(f"AgentRuntime '{agent_id}': Failed to run async final shutdown notification: {run_e}")
        
    async def stop(self, timeout: float = 10.0) -> None:
        agent_id = self.context.agent_id
        if not self._worker.is_alive() and not self._worker._is_active: 
            if not self.context.current_phase.is_terminal():
                await self.phase_manager.notify_final_shutdown_complete()
            return
        
        await self.phase_manager.notify_shutdown_initiated() 
        await self._worker.stop(timeout=timeout) 
        
        if self.context.llm_instance and hasattr(self.context.llm_instance, 'cleanup'):
            cleanup_func = self.context.llm_instance.cleanup
            if asyncio.iscoroutinefunction(cleanup_func): await cleanup_func()
            else: cleanup_func()
        
        await self.phase_manager.notify_final_shutdown_complete() 
        logger.info(f"AgentRuntime for '{agent_id}' stop() method completed.")

    @property 
    def current_phase_property(self) -> AgentOperationalPhase: 
        return self.context.current_phase 
        
    @property
    def is_running(self) -> bool:
        return self._worker.is_alive()
