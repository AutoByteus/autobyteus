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

        Args:
            directory_traversal (DirectoryTraversal): An instance of DirectoryTraversal.
        """
        self.workspace_settings = {}
        self.directory_traversal = DirectoryTraversal()

    def add_workspace(self, workspace_root_path: str) -> TreeNode:
        """
        Adds a workspace setting to the workspace settings and returns the directory tree of the workspace.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            TreeNode: The root TreeNode of the directory tree.

        Raises:
            ValueError: If the workspace could not be added.
        """
        try:
            workspace_setting = WorkspaceSetting(root_path=workspace_root_path)  # Create the workspace setting object
            self.workspace_settings[workspace_root_path] = workspace_setting
        except Exception as e:
            logging.error(f"Error while adding workspace setting: {e}")
            raise ValueError(f"Error while adding workspace setting: {e}")

        try:
            directory_tree = self.directory_traversal.build_tree(workspace_root_path)
            return directory_tree
        except Exception as e:
            logging.error(f"Error while building directory tree: {e}")
            raise ValueError(f"Error while building directory tree: {e}")

    def get_workspace_setting(self, workspace_root_path: str) -> Optional[WorkspaceSetting]:
        """
        Retrieves a workspace setting from the workspace settings.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            Optional[WorkspaceSetting]: The workspace setting if it exists, None otherwise.
        """
        return self.workspace_settings.get(workspace_root_path, None)

    