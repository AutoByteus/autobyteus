# config.py

import os
import yaml

from src.config.config_parser import ConfigParser, TOMLConfigParser
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
    def _read_config_file(self, config_file: str, parser: ConfigParser) -> dict:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
        try:
            return parser.parse(config_file)
        except Exception as e:
            raise ValueError(f"Error reading configuration file '{config_file}': {e}")

    def get(self, key: str, default=None):
        return self.config_data.get(key, default)
    
config = Config()
