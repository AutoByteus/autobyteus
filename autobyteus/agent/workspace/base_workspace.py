# file: autobyteus/autobyteus/agent/workspace/base_workspace.py
import logging
from abc import ABC # Import ABC directly
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class BaseAgentWorkspace(ABC):
    """
    Abstract base class for an agent's workspace or working environment.
    
    This class serves as a common ancestor and type hint for various workspace
    implementations. Concrete subclasses will define the specific capabilities
    and methods relevant to their environment (e.g., file operations,
    database access, specialized tool interactions).
    """

    def __init__(self, agent_id: str, workspace_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the BaseAgentWorkspace.

        Args:
            agent_id: The ID of the agent this workspace belongs to.
            workspace_id: An optional unique identifier for this workspace instance.
                          If None, a default will be generated based on agent_id.
            config: Optional configuration for the workspace (e.g., base path, credentials).
        """
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("BaseAgentWorkspace requires a non-empty string 'agent_id'.")
        
        self._agent_id: str = agent_id
        # Ensure workspace_id is a string if not None
        if workspace_id is not None and not isinstance(workspace_id, str):
            raise ValueError("workspace_id must be a string if provided.")
            
        self._workspace_id: str = workspace_id or f"{agent_id}_default_workspace"
        self._config: Dict[str, Any] = config or {}
        logger.info(f"BaseAgentWorkspace initialized for agent_id '{self._agent_id}', workspace_id '{self._workspace_id}'.")

    @property
    def agent_id(self) -> str:
        """The ID of the agent this workspace belongs to."""
        return self._agent_id

    @property
    def workspace_id(self) -> str:
        """The unique identifier for this workspace instance."""
        return self._workspace_id

    @property
    def config(self) -> Dict[str, Any]:
        """Configuration for the workspace. Implementations can use this as needed."""
        return self._config

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} agent_id='{self.agent_id}', workspace_id='{self.workspace_id}'>"
