"""
This module defines the WorkspaceDefinition class, which encapsulates the metadata
for a specific type of agent workspace.
"""
import logging
from typing import Type, Optional, TYPE_CHECKING
from autobyteus.tools.parameter_schema import ParameterSchema

if TYPE_CHECKING:
    from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace

logger = logging.getLogger(__name__)

class WorkspaceDefinition:
    """Represents the definition of a discoverable and creatable agent workspace type."""
    def __init__(self,
                 workspace_type_name: str,
                 description: str,
                 workspace_class: Type['BaseAgentWorkspace'],
                 config_schema: ParameterSchema):
        if not all([workspace_type_name, description, workspace_class, config_schema is not None]):
            raise ValueError("All parameters for WorkspaceDefinition are required.")

        self.workspace_type_name = workspace_type_name
        self.description = description
        self.workspace_class = workspace_class
        self.config_schema = config_schema
        logger.debug(f"WorkspaceDefinition created for type '{workspace_type_name}'.")

    def to_dict(self) -> dict:
        """Serializes the definition to a dictionary for API exposure."""
        return {
            "workspace_type_name": self.workspace_type_name,
            "description": self.description,
            "config_schema": self.config_schema.to_dict()
        }
