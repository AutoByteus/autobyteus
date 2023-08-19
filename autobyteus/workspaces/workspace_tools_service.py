"""
This module provides the WorkspaceToolsService class which offers tools and operations related to workspaces.
The service encapsulates operations like refactoring and indexing for a given workspace by utilizing other
components such as the WorkspaceSettingRegistry, WorkspaceRefactorer, and other workspace tools.

Importantly, the service fetches tools tailored to a specific workspace's setting, ensuring that the frontend
receives contextually relevant tool information.
"""

import logging
from typing import List
from src.singleton import SingletonMeta
from src.workspaces.setting.workspace_setting_registry import WorkspaceSettingRegistry
from src.workspaces.workspace_tools.types import WorkspaceToolData
from src.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool
from src.workspaces.workspace_tools.workspace_refactorer.workspace_refactorer import WorkspaceRefactorer
from src.automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.workspaces.workspace_tools.workspace_tools_registry import WorkspaceToolsRegistry

class WorkspaceToolsService(metaclass=SingletonMeta):
    """
    Service to provide tools related to workspaces. This service encapsulates
    operations like refactoring and indexing for a given workspace.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setting_registry = WorkspaceSettingRegistry()

    def refactor_workspace(self, workspace_root_path: str):
        """
        Refactor the code within a given workspace.
        
        Args:
            workspace_root_path (str): The root path of the workspace to be refactored.
        """
        try:
            self.logger.info(f"Starting refactoring for workspace at {workspace_root_path}")
            
            # Fetch the workspace setting
            workspace_setting = self.setting_registry.get_setting(workspace_root_path)
            if not workspace_setting:
                self.logger.warning(f"No workspace setting found for {workspace_root_path}. Refactoring skipped.")
                return

            # Use WorkspaceRefactorer to refactor the workspace
            refactorer = WorkspaceRefactorer(workspace_setting)
            refactorer.execute()
            
            self.logger.info(f"Completed refactoring for workspace at {workspace_root_path}")
        except Exception as e:
            self.logger.error(f"Error while refactoring workspace at {workspace_root_path}: {e}")

    def index_workspace(self, workspace_root_path: str):
        """
        Index the code within a given workspace.
        
        Args:
            workspace_root_path (str): The root path of the workspace to be indexed.
        """
        # Placeholder for indexing logic
        pass

    def get_available_tools(self, workspace_root_path: str) -> List[WorkspaceToolData]:
        """
        Fetch the names and prompts of all available workspace tools tailored to a specific workspace's setting.

        Args:
            workspace_root_path (str): The root path of the workspace for which tools are requested.

        Returns:
            list[dict]: List containing dictionary representations of all available workspace tools.
        """
        workspace_setting = self.setting_registry.get_setting(workspace_root_path)
        if not workspace_setting:
            self.logger.warning(f"No workspace setting found for {workspace_root_path}. No tools available.")
            return []

        tools = WorkspaceToolsRegistry.get_all_tools()
        return [WorkspaceToolData(name=tool_cls.name, prompt_template=tool_cls(workspace_setting).prompt_template) for tool_cls in tools]
