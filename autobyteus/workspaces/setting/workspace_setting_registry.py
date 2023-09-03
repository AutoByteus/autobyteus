# autobyteus/workspaces/setting/workspace_setting_registry.py
"""
This module provides a registry for storing workspace settings.

Workspace settings are stored in a dictionary, with the root path of a workspace as the key, 
and the corresponding WorkspaceSetting object as the value.
"""

from typing import Dict, Optional
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.workspaces.setting.workspace_setting import WorkspaceSetting


class WorkspaceSettingRegistry(metaclass=SingletonMeta):
    """
    A registry to store workspace settings.

    Attributes:
        settings (Dict[str, WorkspaceSetting]): A dictionary mapping workspace root paths to 
            their corresponding WorkspaceSetting.
    """

    def __init__(self):
        """
        Initialize WorkspaceSettingRegistry.
        """
        self.settings: Dict[str, WorkspaceSetting] = {}

    def add_setting(self, workspace_root_path: str, setting: WorkspaceSetting) -> None:
        """
        Adds a workspace setting to the registry.

        Args:
            workspace_root_path (str): The root path of the workspace.
            setting (WorkspaceSetting): The workspace setting to be added.
        """
        self.settings[workspace_root_path] = setting

    def get_setting(self, workspace_root_path: str) -> Optional[WorkspaceSetting]:
        """
        Retrieves a workspace setting from the registry.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            Optional[WorkspaceSetting]: The workspace setting if it exists, None otherwise.
        """
        return self.settings.get(workspace_root_path)

    def workspace_exists(self, workspace_root_path: str) -> bool:
        """
        Checks if a workspace setting already exists in the registry.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            bool: True if the workspace setting exists, False otherwise.
        """
        return workspace_root_path in self.settings
