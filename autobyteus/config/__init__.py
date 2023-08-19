# config.py

import os
from typing import Dict
import yaml

from src.config.config_parser import ConfigParser, TOMLConfigParser
from src.workspaces.setting.workspace_setting import WorkspaceSetting
from src.singleton import SingletonMeta


from src.config.config_parser import ConfigParser, ENVConfigParser

class Config(metaclass=SingletonMeta):
    """
    Config is a Singleton class that reads and stores configuration data
    from a file using a ConfigParser. The data can be accessed using the 'get' method.
    """

    def __init__(self, config_file: str = None, parser: ConfigParser = ENVConfigParser()):
        if not config_file:
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..', '.env')
        self.config_data = self._read_config_file(config_file, parser)
        self.workspaces: Dict[str, WorkspaceSetting] = {}  # Add this line

    def _read_config_file(self, config_file: str, parser: ConfigParser) -> dict:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
        try:
            return parser.parse(config_file)
        except Exception as e:
            raise ValueError(f"Error reading configuration file '{config_file}': {e}")

    def get(self, key: str, default=None):
        return self.config_data.get(key, default)
    
    def set(self, key: str, value: str):
        self.config_data.get(key, value)

    
    def add_workspace_root_path(self, workspace_name: str, workspace_setting: WorkspaceSetting):
        """
        Adds a new workspace setting to the global config.

        Args:
            workspace_name (str): The name or identifier of the workspace.
            workspace_setting (WorkspaceSetting): The workspace setting to add.
        """
        self.workspaces[workspace_name] = workspace_setting
    
config = Config()
