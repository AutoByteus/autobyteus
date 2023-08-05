# workspace_setting_registry.py

from typing import Optional
from src.singleton import SingletonMeta
from src.workspaces.setting.workspace_setting import WorkspaceSetting

class WorkspaceSettingRegistry(metaclass=SingletonMeta):
    def __init__(self):
        self._settings = {}

    def add_setting(self, root_path: str, setting: WorkspaceSetting):
        self._settings[root_path] = setting

    def get_setting(self, root_path: str) -> Optional[WorkspaceSetting]:
        return self._settings.get(root_path)

    def remove_setting(self, root_path: str):
        if root_path in self._settings:
            del self._settings[root_path]
