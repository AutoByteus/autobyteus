from abc import ABC, abstractmethod
import yaml
import toml


class ConfigParser(ABC):
    """
    ConfigParser is an abstract base class for configuration file parsers.
    """

    @abstractmethod
    def parse(self, config_file: str) -> dict:
        pass


class YAMLConfigParser(ConfigParser):
    """
    YAMLConfigParser is a class that parses YAML configuration files.
    """

    def parse(self, config_file: str) -> dict:
        with open(config_file, "r") as file:
            return yaml.safe_load(file)


class TOMLConfigParser(ConfigParser):
    """
    TOMLConfigParser is a class that parses TOML configuration files.
    """

    def parse(self, config_file: str) -> dict:
        with open(config_file, "r") as file:
            return toml.load(file)
