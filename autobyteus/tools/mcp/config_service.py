# file: autobyteus/autobyteus/mcp/config_service.py
import logging
import json
import os
from typing import List, Dict, Any, Optional, Union

# Import config types from the types module
from .types import McpConfig, McpTransportType, StdioServerParametersConfig, SseTransportConfig, StreamableHttpConfig

logger = logging.getLogger(__name__)

class McpConfigService:
    """Loads, validates, and provides McpConfig objects."""

    def __init__(self):
        self._configs: Dict[str, McpConfig] = {}
        logger.info("McpConfigService initialized.")

    def _process_config_dict(self, server_identifier: str, config_data: Dict[str, Any]) -> McpConfig: # Renamed config_id to server_identifier for clarity
        """
        Helper to create McpConfig from a dictionary, injecting the server_name.
        The provided 'server_identifier' (typically the key from a config map or 'server_name' field) is
        considered the authoritative identifier for this configuration.
        """
        if not isinstance(config_data, dict):
            raise ValueError(f"Config data for server_identifier '{server_identifier}' must be a dictionary.")
        
        # The 'server_identifier' is used as the 'server_name' for the McpConfig object.
        # This ensures that the key/identifier is the authoritative source for server_name.
        # If 'config_data' were to contain a 'server_name' field, it would be
        # effectively overwritten by 'server_identifier' here.
        final_config_data = {'server_name': server_identifier, **config_data} # UPDATED: 'id' to 'server_name'
        
        # McpConfig itself will handle the instantiation of nested StdioServerParametersConfig,
        # SseTransportConfig, or StreamableHttpConfig from dicts if provided,
        # as well as McpTransportType conversion from string.
        return McpConfig(**final_config_data)


    def load_configs(self, source: Union[str, List[Dict[str, Any]], Dict[str, Any]]) -> List[McpConfig]:
        """
        Loads MCP configurations from various source types.
        Source can be:
        1. A file path (str) to a JSON file. The JSON file can contain:
           a. A list of MCP server configuration dictionaries (each dict must include a "server_name").
           b. A dictionary where keys are server names and values are configurations.
              In this case, the dictionary key is used as the McpConfig 'server_name', and any 'server_name'
              field within the value dictionary is overridden.
        2. A direct list of MCP server configuration dictionaries (List[Dict[str, Any]]).
           Each dictionary in the list must have a 'server_name' field.
        3. A direct dictionary where keys are server names and values are configurations (Dict[str, Any]).
           The dictionary key is used as the McpConfig 'server_name'.

        Args:
            source: Data source for configurations.

        Returns:
            A list of loaded McpConfig objects. Stores unique configs by server_name internally.

        Raises:
            FileNotFoundError: If source is a path and the file is not found.
            ValueError: If configuration data is invalid or JSON is malformed.
            TypeError: If the source type is unsupported.
        """
        loaded_mcp_configs: List[McpConfig] = []
        
        if isinstance(source, str): # File path
            if not os.path.exists(source):
                logger.error(f"MCP configuration file not found at path: {source}")
                raise FileNotFoundError(f"MCP configuration file not found: {source}")
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                logger.info(f"Successfully loaded JSON data from file: {source}")
                return self.load_configs(json_data) 
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from MCP configuration file {source}: {e}")
                raise ValueError(f"Invalid JSON in MCP configuration file {source}: {e}") from e
            except Exception as e: 
                logger.error(f"Error reading MCP configuration file {source}: {e}")
                raise ValueError(f"Could not read MCP configuration file {source}: {e}") from e

        elif isinstance(source, list): # List of config dicts
            logger.info(f"Loading {len(source)} MCP server configurations from provided list.")
            for i, config_dict in enumerate(source):
                if not isinstance(config_dict, dict):
                    raise ValueError(f"Item at index {i} in source list is not a dictionary.")
                # UPDATED: Check for 'server_name' instead of 'id'
                if 'server_name' not in config_dict:
                     raise ValueError(f"Item at index {i} in source list is missing 'server_name' field.")
                try:
                    config = McpConfig(**config_dict)
                    if config.server_name in self._configs: # UPDATED: Use server_name
                        logger.warning(f"Duplicate MCP config server_name '{config.server_name}' found in list. Overwriting previous entry.")
                    self._configs[config.server_name] = config # UPDATED: Use server_name
                    loaded_mcp_configs.append(config)
                    logger.debug(f"Successfully loaded and validated McpConfig for server_name '{config.server_name}' from list.")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid MCP configuration for item at index {i} from list: {e}. Config data: {config_dict}")
                    raise ValueError(f"Invalid MCP configuration data (list item at index {i}): {e}") from e
        
        elif isinstance(source, dict): # Dict of server_name -> config_data
            logger.info(f"Loading MCP server configurations from provided dictionary (assumed to be server_name -> config_data map).")
            for server_config_key, config_data_val in source.items(): # server_config_key is the server_name
                if not isinstance(config_data_val, dict):
                     raise ValueError(f"Configuration for server_name '{server_config_key}' must be a dictionary.")
                try:
                    # _process_config_dict will inject 'server_name' from the key (server_config_key) into the config data.
                    config = self._process_config_dict(server_config_key, config_data_val)
                    if config.server_name in self._configs: # server_config_key should be same as config.server_name
                        logger.warning(f"Duplicate MCP config server_name '{config.server_name}' found in dictionary. Overwriting previous entry.")
                    self._configs[config.server_name] = config # UPDATED: Use server_name
                    loaded_mcp_configs.append(config)
                    logger.debug(f"Successfully loaded and validated McpConfig for server_name '{config.server_name}' from dictionary.")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid MCP configuration for server_name '{server_config_key}' from dictionary: {e}. Config data: {config_data_val}")
                    raise ValueError(f"Invalid MCP configuration data (dict entry for server_name '{server_config_key}'): {e}") from e
        else:
            raise TypeError(f"Unsupported source type for McpConfigService.load_configs: {type(source)}. "
                            "Expected file path (str), list of dicts, or dict of dicts.")

        logger.info(f"McpConfigService load_configs completed. {len(loaded_mcp_configs)} new configurations processed. "
                    f"Total unique configs stored: {len(self._configs)}.")
        return loaded_mcp_configs

    def add_config(self, config_input: Union[McpConfig, Dict[str, Any]]) -> McpConfig:
        """
        Adds a single MCP configuration to the service.
        The configuration can be provided as an McpConfig object or as a dictionary.
        If a dictionary is provided, it must contain a 'server_name' field.
        If a configuration with the same server_name already exists, it will be overwritten,
        and a warning will be logged.

        Args:
            config_input: An McpConfig object or a dictionary representing the config.

        Returns:
            The added or updated McpConfig object.

        Raises:
            ValueError: If config_input is a dict and is missing the 'server_name' field,
                        or if the data is otherwise invalid for McpConfig creation.
            TypeError: If config_input is not an McpConfig or a dict.
        """
        new_config: McpConfig

        if isinstance(config_input, McpConfig):
            new_config = config_input
            logger.debug(f"Attempting to add provided McpConfig object with server_name: '{new_config.server_name}'.") # UPDATED

        elif isinstance(config_input, dict):
            # UPDATED: Check for 'server_name', log with server_name
            config_server_name_for_log = config_input.get('server_name', 'SERVER_NAME_MISSING_IN_DICT')
            logger.debug(f"Attempting to add McpConfig from dictionary. Provided server_name (if any): '{config_server_name_for_log}'.")
            if 'server_name' not in config_input:
                raise ValueError("Configuration dictionary must contain a 'server_name' field.")
            try:
                new_config = McpConfig(**config_input)
            except (ValueError, TypeError) as e: 
                logger.error(f"Invalid MCP configuration data in provided dictionary for server_name '{config_server_name_for_log}': {e}. Data: {config_input}")
                raise ValueError(f"Invalid MCP configuration data in dictionary for server_name '{config_server_name_for_log}': {e}") from e
        else:
            raise TypeError(f"Unsupported input type for add_config: {type(config_input)}. "
                            "Expected McpConfig object or dictionary.")

        if new_config.server_name in self._configs: # UPDATED: Use server_name
            logger.warning(f"Overwriting existing MCP config with server_name '{new_config.server_name}'.")
        
        self._configs[new_config.server_name] = new_config # UPDATED: Use server_name
        logger.info(f"Successfully added/updated McpConfig for server_name '{new_config.server_name}'. " # UPDATED
                    f"Total unique configs stored: {len(self._configs)}.")
        return new_config

    def get_config(self, server_name: str) -> Optional[McpConfig]: # Renamed server_id to server_name for clarity
        """
        Retrieves an MCP configuration by its unique server name.
        Args:
            server_name: The unique name of the MCP server configuration.
        Returns:
            The McpConfig object if found, otherwise None.
        """
        config = self._configs.get(server_name)
        if not config:
            logger.debug(f"McpConfig not found for server_name: '{server_name}'.") # UPDATED
        return config

    def get_all_configs(self) -> List[McpConfig]:
        return list(self._configs.values())

    def clear_configs(self) -> None:
        self._configs.clear()
        logger.info("All MCP configurations cleared from McpConfigService.")
