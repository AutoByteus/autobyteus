# file: autobyteus/autobyteus/workflow/bootstrap_steps/agent_tool_injection_step.py
import logging
from typing import TYPE_CHECKING, Dict, Set

from autobyteus.workflow.bootstrap_steps.base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.workflow.context.workflow_node_config import WorkflowNodeConfig
from autobyteus.tools.registry import default_tool_registry

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class AgentToolInjectionStep(BaseWorkflowBootstrapStep):
    """
    Bootstrap step to inject workflow-aware tools like SendMessageTo into
    agent configurations just before they are used. This step is now effectively
    a placeholder as tool injection is handled just-in-time by the TeamManager,
    but it is kept for potential future use and to maintain the bootstrap sequence structure.
    The primary logic of applying the coordinator prompt has been moved to the TeamManager
    to ensure it happens just before the coordinator is created.
    """
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing AgentToolInjectionStep (now a placeholder).")
        # The logic for injecting SendMessageTo and setting the coordinator prompt is now
        # handled just-in-time by the TeamManager to better support lazy-loading of nodes.
        # This step is preserved in the bootstrap sequence for clarity and future expansion.
        logger.debug(f"Workflow '{workflow_id}': Tool injection and prompt setting are deferred to TeamManager.")
        return True

