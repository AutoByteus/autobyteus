# src/workspaces/workspace_service.py
"""
This module provides a service for handling operations related to workspaces.

This service is responsible for adding workspaces, building their directory structures, 
and maintaining their settings. A workspace is represented by its root path, 
and its setting is stored in a dictionary, with the root path as the key. 
Upon successful addition of a workspace, a directory tree structure represented 
by TreeNode objects is returned.
"""

import logging
from typing import Dict, Optional
from src.singleton import SingletonMeta

from src.source_code_tree.file_explorer.directory_traversal import DirectoryTraversal
from src.source_code_tree.file_explorer.sort_strategy.default_sort_strategy import DefaultSortStrategy
from src.source_code_tree.file_explorer.traversal_ignore_strategy.git_ignore_strategy import GitIgnoreStrategy
from src.source_code_tree.file_explorer.traversal_ignore_strategy.specific_folder_ignore_strategy import SpecificFolderIgnoreStrategy
from src.workspaces.errors.workspace_already_exists_error import WorkspaceAlreadyExistsError
from src.workspaces.setting.project_type_determiner import ProjectTypeDeterminer
from src.workspaces.setting.workspace_setting_registry import WorkspaceSettingRegistry
from src.workspaces.workspace_directory_tree import WorkspaceDirectoryTree
from src.workspaces.setting.workspace_setting import WorkspaceSetting
from src.source_code_tree.file_explorer.tree_node import TreeNode
from src.automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow  # Updated import


logger = logging.getLogger(__name__)

class WorkspaceService(metaclass=SingletonMeta):
    """
    Service to handle operations related to workspaces.

    Attributes:
        workspace_settings_registry (WorkspaceSettingRegistry): A registry to store workspace settings.
        workflows (Dict[str, AutomatedCodingWorkflow]): A dictionary mapping workspace root paths
            to their corresponding AutomatedCodingWorkflow.
    """

    def __init__(self):
        """
        Initialize WorkspaceService.
        """
        self.workspace_settings_registry = WorkspaceSettingRegistry()
        self.project_type_determiner = ProjectTypeDeterminer()
        self.workflows: Dict[str, AutomatedCodingWorkflow] = {}

    def add_workspace(self, workspace_root_path: str) -> TreeNode:
        """
        Adds a workspace setting to the workspace settings, builds the directory tree of the workspace, 
        and initializes an AutomatedCodingWorkflow for the workspace.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            TreeNode: The root TreeNode of the directory tree.

        Raises:
            WorkspaceAlreadyExistsError: If the workspace already exists.
        """
        if self.workspace_settings_registry.workspace_exists(workspace_root_path):
            raise WorkspaceAlreadyExistsError(f"Workspace at {workspace_root_path} already exists")

        # Determine the project type
        project_type = self.project_type_determiner.determine(workspace_root_path)
        workspace_setting = WorkspaceSetting(root_path=workspace_root_path, project_type=project_type)
        directory_tree = self.build_workspace_directory_tree(workspace_root_path)
        workspace_setting.set_directory_tree(WorkspaceDirectoryTree(directory_tree))
        
        # Register the WorkspaceSetting
        self.workspace_settings_registry.add_setting(workspace_root_path, workspace_setting)
        
        # Initialize AutomatedCodingWorkflow with the workspace setting
        self.workflows[workspace_root_path] = AutomatedCodingWorkflow(workspace_setting)

        return directory_tree
    def build_workspace_directory_tree(self, workspace_root_path: str) -> TreeNode:
        """
        Builds and returns the directory tree of a workspace.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            TreeNode: The root TreeNode of the directory tree.
        """

        files_ignore_strategies = [
            SpecificFolderIgnoreStrategy(root_path=workspace_root_path, folders_to_ignore=['.git']),
            GitIgnoreStrategy(root_path=workspace_root_path)
        ]
        self.directory_traversal = DirectoryTraversal(strategies=files_ignore_strategies)

        directory_tree = self.directory_traversal.build_tree(workspace_root_path)
        return directory_tree

    def get_workspace_setting(self, workspace_root_path: str) -> Optional[WorkspaceSetting]:
        """
        Retrieves a workspace setting from the workspace settings registry.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            Optional[WorkspaceSetting]: The workspace setting if it exists, None otherwise.
        """
        return self.workspace_settings_registry.get_setting(workspace_root_path)