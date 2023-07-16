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
from typing import Optional

from src.source_code_tree.file_explorer.directory_traversal import DirectoryTraversal
from src.source_code_tree.file_explorer.traversal_ignore_strategy.git_ignore_strategy import GitIgnoreStrategy
from src.source_code_tree.file_explorer.traversal_ignore_strategy.specific_folder_ignore_strategy import SpecificFolderIgnoreStrategy
from src.workspaces.workspace_directory_tree import WorkspaceDirectoryTree
from src.workspaces.workspace_setting import WorkspaceSetting
from src.source_code_tree.file_explorer.tree_node import TreeNode

class WorkspaceService:
    """
    Service to handle operations related to workspaces.

    Attributes:
        workspace_settings (dict): A dictionary to store workspace settings.
            The keys are the root paths of the workspaces,
            and the values are the corresponding workspace settings.
        directory_traversal (DirectoryTraversal): An instance of DirectoryTraversal to create directory trees.
    """

    def __init__(self):
        """
        Initialize WorkspaceService.
        """
        self.workspace_settings = {}

    def add_workspace(self, workspace_root_path: str) -> TreeNode:
        """
        Adds a workspace setting to the workspace settings and builds the directory tree of the workspace.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            TreeNode: The root TreeNode of the directory tree.
        """
        workspace_setting = self._add_workspace_setting(workspace_root_path)
        directory_tree = self.build_workspace_directory_tree(workspace_root_path)
        workspace_setting.set_directory_tree(WorkspaceDirectoryTree(directory_tree))

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
        Retrieves a workspace setting from the workspace settings.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            Optional[WorkspaceSetting]: The workspace setting if it exists, None otherwise.
        """
        return self.workspace_settings.get(workspace_root_path, None)

    def _add_workspace_setting(self, workspace_root_path: str) -> WorkspaceSetting:
        """
        Adds a workspace setting to the workspace settings.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            WorkspaceSetting: The workspace setting that has been added.

        """

        workspace_setting = WorkspaceSetting(root_path=workspace_root_path)
        self.workspace_settings[workspace_root_path] = workspace_setting
        return workspace_setting
       