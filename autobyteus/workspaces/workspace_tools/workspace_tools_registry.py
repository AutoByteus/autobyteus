"""
Module: workspace_tools_registry

This module provides the `WorkspaceToolsRegistry` class, which maintains a registry
of all available workspace tools. Tools can be registered and fetched using this registry.
"""

from typing import List, Type
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool
from autobyteus.workspaces.workspace_tools.workspace_indexer.workspace_indexer import WorkspaceIndexer
from autobyteus.workspaces.workspace_tools.workspace_refactorer.workspace_refactorer import WorkspaceRefactorer
from autobyteus.workspaces.workspace_tools.workspace_scaffolder.workspace_scaffolder import WorkspaceScaffolder  # Assuming this is the correct import for BaseWorkspaceTool

class WorkspaceToolsRegistry(metaclass=SingletonMeta):
    """
    WorkspaceToolsRegistry maintains a registry of all available workspace tools.
    """
    _tools: List[Type[BaseWorkspaceTool]] = []

    @classmethod
    def register_tool(cls, *tool_clses: Type[BaseWorkspaceTool]) -> None:
        """
        Register one or multiple tools to the registry.
        
        Args:
            *tool_clses (type): One or more classes of the tools to be registered.
        """
        for tool_cls in tool_clses:
            if not issubclass(tool_cls, BaseWorkspaceTool):
                raise ValueError(f"Tool {tool_cls.__name__} is not a subclass of BaseWorkspaceTool")
            cls._tools.append(tool_cls)

    @classmethod
    def get_all_tools(cls) -> List[Type[BaseWorkspaceTool]]:
        """
        Fetch all registered tools.

        Returns:
            list[type]: List of registered tool classes.
        """
        return cls._tools

workspace_tools_registry = WorkspaceToolsRegistry()
workspace_tools_registry.register_tool(WorkspaceScaffolder, 
                                       WorkspaceRefactorer,
                                       WorkspaceIndexer)