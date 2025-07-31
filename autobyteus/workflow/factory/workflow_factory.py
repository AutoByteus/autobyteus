# file: autobyteus/autobyteus/workflow/factory/workflow_factory.py
import logging
import uuid
from typing import Optional, Dict, List

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.context.workflow_config import WorkflowConfig
from autobyteus.workflow.context.workflow_context import WorkflowContext
from autobyteus.workflow.context.workflow_runtime_state import WorkflowRuntimeState
from autobyteus.workflow.context.team_manager import TeamManager
from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
from autobyteus.workflow.handlers.workflow_event_handler_registry import WorkflowEventHandlerRegistry
from autobyteus.workflow.handlers.process_user_message_event_handler import ProcessUserMessageEventHandler
from autobyteus.workflow.handlers.lifecycle_workflow_event_handler import LifecycleWorkflowEventHandler
from autobyteus.workflow.handlers.inter_agent_message_request_event_handler import InterAgentMessageRequestEventHandler
from autobyteus.workflow.handlers.tool_approval_workflow_event_handler import ToolApprovalWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import (
    ProcessUserMessageEvent,
    WorkflowReadyEvent,
    WorkflowErrorEvent,
    InterAgentMessageRequestEvent,
    ToolApprovalWorkflowEvent
)

logger = logging.getLogger(__name__)

class WorkflowFactory(metaclass=SingletonMeta):
    """
    A singleton factory for creating and managing AgenticWorkflow instances.
    It orchestrates the assembly of all core workflow components.
    """
    def __init__(self):
        self._active_workflows: Dict[str, AgenticWorkflow] = {}
        logger.info("WorkflowFactory (Singleton) initialized.")

    def _get_default_event_handler_registry(self) -> WorkflowEventHandlerRegistry:
        """Returns a registry with default handlers for a new workflow."""
        registry = WorkflowEventHandlerRegistry()
        registry.register(ProcessUserMessageEvent, ProcessUserMessageEventHandler())
        registry.register(InterAgentMessageRequestEvent, InterAgentMessageRequestEventHandler())
        registry.register(ToolApprovalWorkflowEvent, ToolApprovalWorkflowEventHandler())
        lifecycle_handler = LifecycleWorkflowEventHandler()
        registry.register(WorkflowReadyEvent, lifecycle_handler)
        registry.register(WorkflowErrorEvent, lifecycle_handler)
        return registry

    def create_workflow(self, config: WorkflowConfig) -> AgenticWorkflow:
        """
        Creates a new workflow based on the provided WorkflowConfig, stores it,
        and returns its facade (AgenticWorkflow).
        """
        if not isinstance(config, WorkflowConfig):
            raise TypeError(f"Expected WorkflowConfig instance, got {type(config).__name__}.")

        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        while workflow_id in self._active_workflows:
            workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"

        # --- Component Assembly as per new architecture ---
        state = WorkflowRuntimeState(workflow_id=workflow_id)
        context = WorkflowContext(workflow_id=workflow_id, config=config, state=state)
        
        handler_registry = self._get_default_event_handler_registry()
        runtime = WorkflowRuntime(context=context, event_handler_registry=handler_registry)
        
        team_manager = TeamManager(
            workflow_id=workflow_id,
            runtime=runtime,
            multiplexer=runtime.multiplexer # Pass multiplexer created in runtime
        )
        
        context.state.team_manager = team_manager
        
        workflow = AgenticWorkflow(runtime=runtime)
        
        self._active_workflows[workflow_id] = workflow
        logger.info(f"Workflow '{workflow_id}' created and stored successfully.")
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[AgenticWorkflow]:
        """Retrieves an active workflow instance by its ID."""
        return self._active_workflows.get(workflow_id)

    async def remove_workflow(self, workflow_id: str, shutdown_timeout: float = 10.0) -> bool:
        """
        Removes a workflow from the factory's management and gracefully stops it.
        """
        workflow = self._active_workflows.pop(workflow_id, None)
        if workflow:
            logger.info(f"Removing workflow '{workflow_id}'. Attempting graceful shutdown.")
            await workflow.stop(timeout=shutdown_timeout)
            return True
        logger.warning(f"Workflow with ID '{workflow_id}' not found for removal.")
        return False

    def list_active_workflow_ids(self) -> List[str]:
        """Returns a list of IDs of all active workflows managed by this factory."""
        return list(self._active_workflows.keys())
