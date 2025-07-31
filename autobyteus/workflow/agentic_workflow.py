# file: autobyteus/autobyteus/workflow/agentic_workflow.py
import logging
from typing import Optional

from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent, ToolApprovalWorkflowEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase

logger = logging.getLogger(__name__)

class AgenticWorkflow:
    """
    User-facing facade for interacting with a managed workflow.
    This class is a lightweight wrapper around a WorkflowRuntime instance
    and is typically created by a WorkflowFactory.
    """
    def __init__(self, runtime: WorkflowRuntime):
        """
        Initializes the AgenticWorkflow facade.

        Args:
            runtime: The pre-configured and ready-to-use runtime for the workflow.
        """
        if not isinstance(runtime, WorkflowRuntime):
            raise TypeError(f"AgenticWorkflow requires a WorkflowRuntime instance, got {type(runtime).__name__}")
        
        self._runtime = runtime
        self.workflow_id: str = self._runtime.context.workflow_id
        logger.info(f"AgenticWorkflow facade created for workflow ID '{self.workflow_id}'.")

    @property
    def name(self) -> str:
        return self._runtime.context.config.name

    @property
    def role(self) -> Optional[str]:
        """The role of the workflow, for when it's used as a sub-workflow."""
        return self._runtime.context.config.role

    async def post_message(self, message: AgentInputUserMessage, target_agent_name: Optional[str] = None) -> None:
        """
        Submits a message to the workflow, routing it to a specific node (agent or sub-workflow).
        If `target_agent_name` is not provided, the message is sent to the workflow's coordinator.
        """
        final_target_name = target_agent_name or self._runtime.context.config.coordinator_node.name
        logger.info(f"Workflow '{self.workflow_id}': post_message called. Target: '{final_target_name}'.")

        if not self._runtime.is_running:
            self.start()
        
        event = ProcessUserMessageEvent(
            user_message=message,
            target_agent_name=final_target_name
        )
        await self._runtime.submit_event(event)

    async def post_tool_execution_approval(
        self,
        agent_name: str,
        tool_invocation_id: str,
        is_approved: bool,
        reason: Optional[str] = None
    ):
        """Submits a tool execution approval/denial to a specific agent in the workflow."""
        logger.info(f"Workflow '{self.workflow_id}': post_tool_execution_approval called for agent '{agent_name}'. Approved: {is_approved}.")
        if not self._runtime.is_running:
            logger.warning(f"Workflow '{self.workflow_id}' is not running. Cannot post approval.")
            return

        event = ToolApprovalWorkflowEvent(
            agent_name=agent_name,
            tool_invocation_id=tool_invocation_id,
            is_approved=is_approved,
            reason=reason,
        )
        await self._runtime.submit_event(event)

    def start(self) -> None:
        """Starts the workflow's background worker thread."""
        self._runtime.start()

    async def stop(self, timeout: float = 10.0) -> None:
        """Stops the workflow and all its agents."""
        await self._runtime.stop(timeout)

    @property
    def is_running(self) -> bool:
        """Checks if the workflow's worker is running."""
        return self._runtime.is_running
        
    def get_current_phase(self) -> WorkflowOperationalPhase: 
        return self._runtime.context.state.current_phase
