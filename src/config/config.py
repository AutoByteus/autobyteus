# config.py

import os
import yaml

from src.config.config_parser import ConfigParser, TOMLConfigParser

class SingletonMeta(type):
    """
    SingletonMeta is a metaclass that implements the Singleton design pattern.
    It ensures that a class using this metaclass can have only one instance.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Config(metaclass=SingletonMeta):
    """
    Config is a Singleton class that reads and stores configuration data
    from a file using a ConfigParser. The data can be accessed using the 'get' method.
    """
    
    def __init__(self, config_file: str = None, parser: ConfigParser = TOMLConfigParser()):
        if not config_file:
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.toml')
        self.config_data = self._read_config_file(config_file, parser)

    def _read_config_file(self, config_file: str, parser: ConfigParser) -> dict:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
        try:
            return parser.parse(config_file)
        except Exception as e:
            raise ValueError(f"Error reading configuration file '{config_file}': {e}")

    def get(self, key: str):
        return self.config_data.get(key)
    
config = Config()
