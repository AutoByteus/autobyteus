# file: autobyteus/autobyteus/agent/workspace/base_workspace.py
import logging
from abc import ABC
from typing import Optional, Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class BaseAgentWorkspace(ABC):
    """
    Abstract base class for an agent's workspace or working environment.
    
    This class serves as a common ancestor and type hint for various workspace
    implementations. The AgentContext is injected into this object during the
    agent's bootstrap process.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the BaseAgentWorkspace.

        Args:
            config: Optional configuration for the workspace (e.g., base path, credentials).
        """
        self._config: Dict[str, Any] = config or {}
        self.context: Optional['AgentContext'] = None
        
        logger.info("BaseAgentWorkspace initialized. Context pending injection.")

    def set_context(self, context: 'AgentContext'):
        """
        Injects the agent's context into the workspace.
        This is called during the agent's bootstrap process.
        """
        if self.context:
            logger.warning(f"Workspace for agent '{self.agent_id}' is having its context overwritten. This is unusual.")
        self.context = context
        logger.info(f"AgentContext for agent '{self.agent_id}' injected into workspace.")

    @property
    def agent_id(self) -> Optional[str]:
        """The ID of the agent this workspace belongs to. Returns None if context is not set."""
        if self.context:
            return self.context.agent_id
        return None

    @property
    def config(self) -> Dict[str, Any]:
        """Configuration for the workspace. Implementations can use this as needed."""
        return self._config

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} agent_id='{self.agent_id or 'N/A'}>"
