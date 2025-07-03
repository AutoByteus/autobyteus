"""
This module contains the metaclass for BaseAgentWorkspace for automatic registration.
"""
import logging
from abc import ABCMeta
from .workspace_registry import default_workspace_registry
from .workspace_definition import WorkspaceDefinition

logger = logging.getLogger(__name__)

class WorkspaceMeta(ABCMeta):
    """Metaclass to automatically register concrete BaseAgentWorkspace subclasses."""
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        
        if name == 'BaseAgentWorkspace' or getattr(cls, "__abstractmethods__", None):
            logger.debug(f"Skipping registration for abstract workspace class: {name}")
            return

        try:
            workspace_type_name = cls.get_workspace_type_name()
            description = cls.get_description()
            config_schema = cls.get_config_schema()
            
            definition = WorkspaceDefinition(
                workspace_type_name=workspace_type_name,
                description=description,
                workspace_class=cls,
                config_schema=config_schema
            )
            default_workspace_registry.register(definition)
            config_params_info = f"config_params: {len(config_schema) if config_schema else 0}"
            logger.info(f"Auto-registered workspace: '{workspace_type_name}' from class {name} ({config_params_info})")
        except AttributeError as e:
            logger.error(f"Workspace class {name} is missing a required static/class method ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register workspace class {name}: {e}", exc_info=True)
