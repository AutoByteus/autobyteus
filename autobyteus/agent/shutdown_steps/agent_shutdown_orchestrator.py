# file: autobyteus/autobyteus/agent/shutdown_steps/agent_shutdown_orchestrator.py
import logging
from typing import TYPE_CHECKING, List, Optional

from .base_shutdown_step import BaseShutdownStep
from .llm_instance_cleanup_step import LLMInstanceCleanupStep
from .mcp_server_cleanup_step import McpServerCleanupStep

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class AgentShutdownOrchestrator:
    """
    Orchestrates the agent's shutdown process by executing a sequence of
    self-contained cleanup steps.
    """
    def __init__(self, steps: Optional[List[BaseShutdownStep]] = None):
        """
        Initializes the AgentShutdownOrchestrator.

        Args:
            steps: An optional list of shutdown steps to execute. If not provided,
                   a default sequence will be used.
        """
        if steps is None:
            self.shutdown_steps: List[BaseShutdownStep] = [
                LLMInstanceCleanupStep(),
                McpServerCleanupStep(),
            ]
            logger.debug("AgentShutdownOrchestrator initialized with default steps.")
        else:
            self.shutdown_steps = steps
            logger.debug(f"AgentShutdownOrchestrator initialized with {len(steps)} custom steps.")

    async def run(self, context: 'AgentContext') -> bool:
        """
        Executes the configured sequence of shutdown steps.

        Args:
            context: The agent's context.

        Returns:
            True if all steps completed successfully, False otherwise.
        """
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': AgentShutdownOrchestrator starting execution.")

        for step_index, step_instance in enumerate(self.shutdown_steps):
            step_name = step_instance.__class__.__name__
            logger.debug(f"Agent '{agent_id}': Executing shutdown step {step_index + 1}/{len(self.shutdown_steps)}: {step_name}")
            
            success = await step_instance.execute(context)
            
            if not success:
                error_message = f"Shutdown step {step_name} failed."
                logger.error(f"Agent '{agent_id}': {error_message} Halting shutdown orchestration.")
                # The step itself is responsible for detailed error logging.
                return False

        logger.info(f"Agent '{agent_id}': All shutdown steps completed successfully.")
        return True
