# file: autobyteus/autobyteus/agent/workspace/base_workspace.py
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, TYPE_CHECKING
from autobyteus.tools.parameter_schema import ParameterSchema
from autobyteus.agent.workspace.workspace_meta import WorkspaceMeta
from autobyteus.agent.workspace.workspace_config import WorkspaceConfig

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class BaseAgentWorkspace(ABC, metaclass=WorkspaceMeta):
    """
    Abstract base class for an agent's workspace or working environment.
    
    Subclasses are automatically registered and must implement the class methods
    for self-description (`get_type_name`, `get_description`, `get_config_schema`).
    """

    def __init__(self, config: Optional[WorkspaceConfig] = None):
        """
        Initializes the BaseAgentWorkspace.

        Args:
            config: Optional configuration for the workspace (e.g., base path, credentials).
        """
        self._config: WorkspaceConfig = config or WorkspaceConfig()
        self.context: Optional['AgentContext'] = None
        logger.debug(f"{self.__class__.__name__} instance initialized. Context pending injection.")

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
    def config(self) -> WorkspaceConfig:
        """Configuration for the workspace. Implementations can use this as needed."""
        return self._config

    @classmethod
    @abstractmethod
    def get_type_name(cls) -> str:
        """Returns the unique, machine-readable type name for this workspace (e.g., 'local_file_system')."""
        pass
    
    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """Returns a user-friendly description of this workspace type."""
        pass
    
    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> ParameterSchema:
        """Returns the ParameterSchema defining the configuration arguments needed to create an instance of this workspace."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} agent_id='{self.agent_id or 'N/A'}>"
