# file: autobyteus/autobyteus/workflow/runtime/workflow_runtime.py
import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Optional

from autobyteus.workflow.context.workflow_context import WorkflowContext
from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager
from autobyteus.workflow.runtime.workflow_worker import WorkflowWorker
from autobyteus.workflow.events.workflow_events import BaseWorkflowEvent
from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier
from autobyteus.workflow.streaming.agent_event_multiplexer import AgentEventMultiplexer

if TYPE_CHECKING:
    from autobyteus.workflow.handlers.workflow_event_handler_registry import WorkflowEventHandlerRegistry

logger = logging.getLogger(__name__)

class WorkflowRuntime:
    """The active execution engine for a workflow, managing the worker."""
    def __init__(self, context: WorkflowContext, event_handler_registry: 'WorkflowEventHandlerRegistry'):
        self.context = context
        self.notifier = WorkflowExternalEventNotifier(workflow_id=self.context.workflow_id, runtime_ref=self)
        self.phase_manager = WorkflowPhaseManager(context=self.context, notifier=self.notifier)
        
        # --- FIX: Set the phase_manager_ref on the context's state BEFORE creating the worker ---
        self.context.state.phase_manager_ref = self.phase_manager
        
        self._worker = WorkflowWorker(self.context, event_handler_registry)
        
        self.multiplexer = AgentEventMultiplexer(
            workflow_id=self.context.workflow_id,
            notifier=self.notifier,
            worker_ref=self._worker
        )
        
        # Set other references on the context's state object for access by other components
        self.context.state.multiplexer_ref = self.multiplexer

        self._worker.add_done_callback(self._handle_worker_completion)
        logger.info(f"WorkflowRuntime initialized for workflow '{self.context.workflow_id}'.")

    def get_worker_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Returns the worker's event loop if it's running."""
        return self._worker.get_worker_loop()

    def _handle_worker_completion(self, future: asyncio.Future):
        workflow_id = self.context.workflow_id
        try:
            future.result()
            logger.info(f"WorkflowRuntime '{workflow_id}': Worker thread completed.")
        except Exception as e:
            logger.error(f"WorkflowRuntime '{workflow_id}': Worker thread terminated with exception: {e}", exc_info=True)
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

    async def submit_event(self, event: BaseWorkflowEvent):
        if not self._worker.is_alive:
            raise RuntimeError("Workflow worker is not active.")
        def _coro_factory():
            async def _enqueue():
                from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent
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
