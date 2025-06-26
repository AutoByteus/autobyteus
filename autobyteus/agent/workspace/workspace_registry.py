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
        if definition.type_name in self._definitions:
            logger.warning(f"Overwriting workspace definition for type '{definition.type_name}'.")
        self._definitions[definition.type_name] = definition

    def get_definition(self, type_name: str) -> Optional[WorkspaceDefinition]:
        """Retrieves a workspace definition by its unique type name."""
        return self._definitions.get(type_name)

    def get_all_definitions(self) -> List[WorkspaceDefinition]:
        """Returns a list of all registered workspace definitions."""
        return list(self._definitions.values())

    def create_workspace(self, type_name: str, params: Dict[str, Any]) -> 'BaseAgentWorkspace':
        """
        Creates an instance of a workspace.

        Args:
            type_name (str): The unique type name of the workspace to create.
            params (Dict[str, Any]): A dictionary of parameters for instantiation.

        Returns:
            An instance of a BaseAgentWorkspace subclass.
            
        Raises:
            ValueError: If the type is unknown or parameters are invalid.
        """
        definition = self.get_definition(type_name)
        if not definition:
            raise ValueError(f"Unknown workspace type: '{type_name}'")

        is_valid, errors = definition.config_schema.validate_config(params)
        if not is_valid:
            error_str = ", ".join(errors)
            raise ValueError(f"Invalid parameters for workspace type '{type_name}': {error_str}")

        try:
            workspace_class = definition.workspace_class
            workspace_config = WorkspaceConfig(params=params)
            instance = workspace_class(config=workspace_config)
            logger.info(f"Successfully created instance of workspace type '{type_name}'.")
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate workspace class '{definition.workspace_class.__name__}': {e}", exc_info=True)
            raise RuntimeError(f"Workspace instantiation failed for type '{type_name}': {e}") from e

default_workspace_registry = WorkspaceRegistry()
