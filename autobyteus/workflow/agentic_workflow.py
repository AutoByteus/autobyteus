import logging
from typing import Optional

from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

logger = logging.getLogger(__name__)

class AgenticWorkflow:
    """
    User-facing facade for interacting with a managed workflow.
    This class is now a lightweight wrapper around a WorkflowRuntime instance
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

    async def post_message(self, message: AgentInputUserMessage, target_agent_name: Optional[str] = None) -> None:
        """Submits a message to the workflow, routing it to a specific agent."""
        final_target_name = target_agent_name or self._runtime.context.config.coordinator_node.name
        logger.info(f"Workflow '{self.workflow_id}': post_message called. Target: '{final_target_name}'.")

        if not self._runtime.is_running:
            self.start()
        
        event = ProcessUserMessageEvent(
            user_message=message,
            target_agent_name=final_target_name
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
