# file: autobyteus/autobyteus/agent/bootstrap_steps/agent_bootstrapper.py
import logging
from typing import List, Optional

from .base_bootstrap_step import BaseBootstrapStep
from .workspace_context_initialization_step import WorkspaceContextInitializationStep
from .system_prompt_processing_step import SystemPromptProcessingStep
from .mcp_server_prewarming_step import McpServerPrewarmingStep

logger = logging.getLogger(__name__)

class AgentBootstrapper:
    """
    Provides the ordered bootstrap steps for the agent.
    Execution is driven by bootstrap lifecycle events.
    """
    def __init__(self, steps: Optional[List[BaseBootstrapStep]] = None):
        """
        Initializes the AgentBootstrapper.

        Args:
            steps: An optional list of bootstrap steps to execute. If not provided,
                   a default sequence will be used.
        """
        if steps is None:
            self.bootstrap_steps: List[BaseBootstrapStep] = [
                WorkspaceContextInitializationStep(),
                McpServerPrewarmingStep(),
                SystemPromptProcessingStep(),
            ]
            logger.debug("AgentBootstrapper initialized with default steps.")
        else:
            self.bootstrap_steps = steps
            logger.debug(f"AgentBootstrapper initialized with {len(steps)} custom steps.")
