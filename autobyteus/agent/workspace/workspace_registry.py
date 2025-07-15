"""
This module provides a central registry for agent workspace types.
"""
import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from autobyteus.utils.singleton import SingletonMeta
from .workspace_definition import WorkspaceDefinition
from .workspace_config import WorkspaceConfig

if TYPE_CHECKING:
    from .base_workspace import BaseAgentWorkspace

logger = logging.getLogger(__name__)

class WorkspaceRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for WorkspaceDefinition objects. Workspaces are
    typically auto-registered via WorkspaceMeta.
    """
    def __init__(self):
        self._definitions: Dict[str, WorkspaceDefinition] = {}
        logger.info("Core WorkspaceRegistry initialized.")

    def register(self, definition: WorkspaceDefinition):
        """Registers a workspace definition."""
        if not isinstance(definition, WorkspaceDefinition):
            raise TypeError("Can only register WorkspaceDefinition objects.")
        if definition.workspace_type_name in self._definitions:
            logger.warning(f"Overwriting workspace definition for type '{definition.workspace_type_name}'.")
        self._definitions[definition.workspace_type_name] = definition

    def get_definition(self, workspace_type_name: str) -> Optional[WorkspaceDefinition]:
        """Retrieves a workspace definition by its unique type name."""
        return self._definitions.get(workspace_type_name)

    def get_all_definitions(self) -> List[WorkspaceDefinition]:
        """Returns a list of all registered workspace definitions."""
        return list(self._definitions.values())

    def create_workspace(self, workspace_type_name: str, config: WorkspaceConfig) -> 'BaseAgentWorkspace':
        """
        Creates an instance of a workspace.

        Args:
            workspace_type_name (str): The unique type name of the workspace to create.
            config (WorkspaceConfig): The configuration object for the workspace.

        Returns:
            An instance of a BaseAgentWorkspace subclass.
            
        Raises:
            ValueError: If the type is unknown or parameters are invalid.
        """
        definition = self.get_definition(workspace_type_name)
        if not definition:
            raise ValueError(f"Unknown workspace type: '{workspace_type_name}'")

        is_valid, errors = definition.config_schema.validate_config(config.to_dict())
        if not is_valid:
            error_str = ", ".join(errors)
            raise ValueError(f"Invalid parameters for workspace type '{workspace_type_name}': {error_str}")

        try:
            workspace_class = definition.workspace_class
            instance = workspace_class(config=config)
            logger.info(f"Successfully created instance of workspace type '{workspace_type_name}'.")
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate workspace class '{definition.workspace_class.__name__}': {e}", exc_info=True)
            raise RuntimeError(f"Workspace instantiation failed for type '{workspace_type_name}': {e}") from e

default_workspace_registry = WorkspaceRegistry()
