# file: autobyteus/autobyteus/agent/bootstrap_steps/workspace_context_initialization_step.py
import logging
from typing import TYPE_CHECKING

from .base_bootstrap_step import BaseBootstrapStep

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.phases import AgentPhaseManager

logger = logging.getLogger(__name__)

class WorkspaceContextInitializationStep(BaseBootstrapStep):
    """
    Bootstrap step for injecting the AgentContext into the agent's workspace instance.
    """

    def __init__(self):
        logger.debug("WorkspaceContextInitializationStep initialized.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Executing WorkspaceContextInitializationStep.")

        workspace = context.workspace

        if not workspace:
            logger.debug(f"Agent '{agent_id}': No workspace configured. Skipping context injection.")
            return True

        try:
            if hasattr(workspace, 'set_context') and callable(getattr(workspace, 'set_context')):
                workspace.set_context(context)
                logger.info(f"Agent '{agent_id}': AgentContext successfully injected into workspace instance of type '{type(workspace).__name__}'.")
            else:
                logger.warning(f"Agent '{agent_id}': Configured workspace of type '{type(workspace).__name__}' does not have a 'set_context' method. "
                               "Workspace will not have access to the agent's context.")

            return True
        except Exception as e:
            error_message = f"Agent '{agent_id}': Critical failure during WorkspaceContextInitializationStep: {e}"
            logger.error(error_message, exc_info=True)
            # No easy way to enqueue an error event here if queues aren't even initialized yet.
            # The failure of a bootstrap step is handled by the bootstrapper, which will log and set error phase.
            return False
