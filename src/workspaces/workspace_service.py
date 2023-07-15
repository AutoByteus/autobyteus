# src/settings/workspace_service.py
"""
This module provides a service for handling operations related to workspaces.
"""

from typing import Optional

from src.workspaces.workspace_setting import WorkspaceSetting

class WorkspaceService:
    """
    Service to handle operations related to workspaces.

    Attributes:
        workspace_settings (dict): A dictionary to store workspace settings.
            The keys are the root paths of the workspaces,
            and the values are the corresponding workspace settings.
    """

    def __init__(self):
        """
        Initialize WorkspaceService.
        """
        self.workspace_settings = {}

    def add_workspace(self, workspace_root_path: str) -> bool:
        """
        Adds a workspace setting to the workspace settings.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            bool: True if the workspace setting was added successfully, False otherwise.
        """
        try:
            workspace_setting = WorkspaceSetting()  # Create the workspace setting object
            self.workspace_settings[workspace_root_path] = workspace_setting
            return True
        except Exception as e:
            print(f"Error while adding workspace: {e}")
            return False

    def get_workspace_setting(self, workspace_root_path: str) -> Optional[WorkspaceSetting]:
        """
        Retrieves a workspace setting from the workspace settings.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            Optional[WorkspaceSetting]: The workspace setting if it exists, None otherwise.
        """
        return self.workspace_settings.get(workspace_root_path, None)
