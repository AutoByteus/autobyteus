# file: autobyteus/autobyteus/mcp/config_service.py
import logging
import json
import os
from typing import List, Dict, Any, Optional, Union, Type

# Import config types from the types module
from .types import (
    BaseMcpConfig,
    StdioMcpServerConfig,
    SseMcpServerConfig,
    StreamableHttpMcpServerConfig,
    McpTransportType
)
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class McpConfigService(metaclass=SingletonMeta):
    """Loads, validates, and provides MCP Server Configuration objects (BaseMcpConfig and its subclasses)."""

    def __init__(self):
        self._configs: Dict[str, BaseMcpConfig] = {}
        logger.info("McpConfigService initialized.")

    def _parse_transport_type(self, type_str: str, server_identifier: str) -> McpTransportType:
        """Parses string to McpTransportType enum."""
        try:
            return McpTransportType(type_str.lower())
        except ValueError:
            valid_types = [t.value for t in McpTransportType]
            raise ValueError(
                f"Invalid 'transport_type' string '{type_str}' for server '{server_identifier}'. "
                f"Valid types are: {valid_types}."
            )

    def _create_specific_config(self, server_id: str, transport_type: McpTransportType, config_data: Dict[str, Any]) -> BaseMcpConfig:
        """
        Creates a specific McpServerConfig (Stdio, Sse, StreamableHttp) based on transport_type.
        The 'server_id' is injected.
        Parameters from nested structures like 'stdio_params' are un-nested.
        """
        # Start with base parameters that can be at the top level of config_data
        constructor_params = {'server_id': server_id}
        
        # Explicitly copy known BaseMcpConfig fields from config_data if they exist
        for base_key in ['enabled', 'tool_name_prefix']:
            if base_key in config_data:
                constructor_params[base_key] = config_data[base_key]

        # Define keys for nested transport-specific parameters
        transport_specific_params_key_map = {
            McpTransportType.STDIO: "stdio_params",
            McpTransportType.SSE: "sse_params",
            McpTransportType.STREAMABLE_HTTP: "streamable_http_params"
        }

        if transport_type in transport_specific_params_key_map:
            params_key = transport_specific_params_key_map[transport_type]
            specific_params_dict = config_data.get(params_key, {})
            if not isinstance(specific_params_dict, dict):
                raise ValueError(f"'{params_key}' for server '{server_id}' must be a dictionary, got {type(specific_params_dict)}.")
            # Merge extracted specific params into constructor_params
            # This allows specific params (e.g. 'command') to be defined inside the nested dict
            constructor_params.update(specific_params_dict)
        
        # Filter out keys that are not part of the target dataclass or already processed
        # For example, remove 'transport_type' and the 'xxx_params' keys themselves
        # from the final constructor_params if they were top-level in config_data.
        # Note: config_data at this point is the value part of the server_id -> value map,
        # or an item from the list of configs.
        # So, 'transport_type' and 'stdio_params' (etc.) will be keys in it.
        
        # Clean up params_for_constructor by removing original nested dict keys and transport_type
        if transport_type in transport_specific_params_key_map:
            constructor_params.pop(transport_specific_params_key_map[transport_type], None)
        constructor_params.pop('transport_type', None) # From original config_data if it was spread
                                                       # Actually, config_data doesn't have server_id yet.
                                                       # server_id is added to constructor_params at the start.
                                                       # transport_type is not added to constructor_params from config_data.
        
        # This part ensures any other top-level keys in config_data that are valid for the
        # specific config class (but not 'enabled', 'tool_name_prefix', or the nested param dict key itself)
        # are also included.
        # Example: if StdioMcpServerConfig had a field 'priority' that could be in config_data top-level.
        other_top_level_keys_to_copy = {
            k: v for k, v in config_data.items() 
            if k not in ['enabled', 'tool_name_prefix', 'transport_type', 
                         transport_specific_params_key_map.get(McpTransportType.STDIO),
                         transport_specific_params_key_map.get(McpTransportType.SSE),
                         transport_specific_params_key_map.get(McpTransportType.STREAMABLE_HTTP)]
        }
        constructor_params.update(other_top_level_keys_to_copy)


        try:
            if transport_type == McpTransportType.STDIO:
                return StdioMcpServerConfig(**constructor_params)
            elif transport_type == McpTransportType.SSE:
                return SseMcpServerConfig(**constructor_params)
            elif transport_type == McpTransportType.STREAMABLE_HTTP:
                return StreamableHttpMcpServerConfig(**constructor_params)
            else:
                # This path should ideally not be taken if transport_type is validated upfront.
                raise ValueError(f"Unsupported McpTransportType '{transport_type}' for server '{server_id}'. Cannot create specific config.")
        except TypeError as e:
            logger.error(f"TypeError creating config for server '{server_id}' with transport '{transport_type}'. "
                         f"Params: {constructor_params}. Error: {e}", exc_info=True)
            raise ValueError(f"Failed to create config for server '{server_id}' due to incompatible parameters for {transport_type.name} config: {e}")


    def load_configs(self, source: Union[str, List[Dict[str, Any]], Dict[str, Any]]) -> List[BaseMcpConfig]:
        """
        Loads MCP configurations from various source types.
        Source can be:
        1. A file path (str) to a JSON file. The JSON file can contain:
           a. A list of MCP server configuration dictionaries. Each dict must include "server_id" and "transport_type".
           b. A dictionary where keys are server IDs and values are configurations. Each value dict must include "transport_type".
              The dictionary key is used as the McpConfig 'server_id'.
        2. A direct list of MCP server configuration dictionaries (List[Dict[str, Any]]).
           Each dictionary in the list must have "server_id" and "transport_type".
        3. A direct dictionary where keys are server IDs and values are configurations (Dict[str, Any]).
           Each value dict must include "transport_type". The dictionary key is used as the McpConfig 'server_id'.

        Args:
            source: Data source for configurations.

        Returns:
            A list of loaded McpServerConfig objects (subclasses of BaseMcpConfig).
            Stores unique configs by server_id internally.
        """
        loaded_mcp_configs: List[BaseMcpConfig] = []
        
        if isinstance(source, str):
            if not os.path.exists(source):
                logger.error(f"MCP configuration file not found at path: {source}")
                raise FileNotFoundError(f"MCP configuration file not found: {source}")
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                logger.info(f"Successfully loaded JSON data from file: {source}")
                # Recursive call with the parsed JSON data
                return self.load_configs(json_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from MCP configuration file {source}: {e}")
                raise ValueError(f"Invalid JSON in MCP configuration file {source}: {e}") from e
            except Exception as e:
                logger.error(f"Error reading MCP configuration file {source}: {e}")
                raise ValueError(f"Could not read MCP configuration file {source}: {e}") from e

        elif isinstance(source, list):
            logger.info(f"Loading {len(source)} MCP server configurations from provided list.")
            for i, config_item_dict in enumerate(source): # Renamed from config_dict to avoid confusion
                if not isinstance(config_item_dict, dict):
                    raise ValueError(f"Item at index {i} in source list is not a dictionary.")
                
                current_server_id = config_item_dict.get('server_id')
                if not current_server_id:
                     raise ValueError(f"Item at index {i} in source list is missing 'server_id' field.")
                
                transport_type_str = config_item_dict.get('transport_type')
                if not transport_type_str:
                    raise ValueError(f"Item at index {i} (server '{current_server_id}') in source list is missing 'transport_type' field.")

                try:
                    transport_type_enum = self._parse_transport_type(transport_type_str, current_server_id)
                    # Pass the config_item_dict (which contains transport_type, stdio_params etc.)
                    config_obj = self._create_specific_config(current_server_id, transport_type_enum, config_item_dict)
                    
                    if config_obj.server_id in self._configs:
                        logger.warning(f"Duplicate MCP config server_id '{config_obj.server_id}' found in list. Overwriting previous entry.")
                    self._configs[config_obj.server_id] = config_obj
                    loaded_mcp_configs.append(config_obj)
                    logger.debug(f"Successfully loaded and validated {type(config_obj).__name__} for server_id '{config_obj.server_id}' from list.")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid MCP configuration for item at index {i} (server '{current_server_id}') from list: {e}. Config data: {config_item_dict}")
                    raise ValueError(f"Invalid MCP configuration data (list item at index {i}, server '{current_server_id}'): {e}") from e
        
        elif isinstance(source, dict):
            logger.info(f"Loading MCP server configurations from provided dictionary (assumed to be server_id -> config_data map).")
            for server_config_key_id, config_value_dict in source.items(): # Renamed variables for clarity
                if not isinstance(config_value_dict, dict):
                     raise ValueError(f"Configuration for server_id '{server_config_key_id}' must be a dictionary.")

                transport_type_str = config_value_dict.get('transport_type')
                if not transport_type_str:
                    raise ValueError(f"Config data for server '{server_config_key_id}' is missing 'transport_type' field.")

                try:
                    transport_type_enum = self._parse_transport_type(transport_type_str, server_config_key_id)
                    # Pass config_value_dict (which contains transport_type, stdio_params etc.)
                    config_obj = self._create_specific_config(server_config_key_id, transport_type_enum, config_value_dict)

                    if config_obj.server_id in self._configs:
                        logger.warning(f"Duplicate MCP config server_id '{config_obj.server_id}' found in dictionary. Overwriting previous entry.")
                    self._configs[config_obj.server_id] = config_obj
                    loaded_mcp_configs.append(config_obj)
                    logger.debug(f"Successfully loaded and validated {type(config_obj).__name__} for server_id '{config_obj.server_id}' from dictionary.")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid MCP configuration for server_id '{server_config_key_id}' from dictionary: {e}. Config data: {config_value_dict}")
                    raise ValueError(f"Invalid MCP configuration data (dict entry for server_id '{server_config_key_id}'): {e}") from e
        else:
            raise TypeError(f"Unsupported source type for McpConfigService.load_configs: {type(source)}. "
                            "Expected file path (str), list of dicts, or dict of dicts.")

        logger.info(f"McpConfigService load_configs completed. {len(loaded_mcp_configs)} new configurations processed. "
                    f"Total unique configs stored: {len(self._configs)}.")
        return loaded_mcp_configs

    def add_config(self, config_object: BaseMcpConfig) -> BaseMcpConfig:
        """
        Adds a single, pre-instantiated MCP server configuration object to the service.
        The configuration object must be an instance of a BaseMcpConfig subclass
        (e.g., StdioMcpServerConfig, SseMcpServerConfig).
        If a configuration with the same server_id already exists, it will be overwritten.

        Args:
            config_object: A BaseMcpConfig subclass instance (e.g., StdioMcpServerConfig).

        Returns:
            The added or updated McpServerConfig object.

        Raises:
            TypeError: If config_object is not a BaseMcpConfig subclass instance.
        """
        if not isinstance(config_object, BaseMcpConfig):
            raise TypeError(f"Unsupported input type for add_config: {type(config_object)}. "
                            "Expected a BaseMcpConfig subclass object (e.g., StdioMcpServerConfig).")

        logger.debug(f"Attempting to add provided {type(config_object).__name__} object with server_id: '{config_object.server_id}'.")

        if config_object.server_id in self._configs:
            logger.warning(f"Overwriting existing MCP config with server_id '{config_object.server_id}'.")
        
        self._configs[config_object.server_id] = config_object
        logger.info(f"Successfully added/updated {type(config_object).__name__} for server_id '{config_object.server_id}'. "
                    f"Total unique configs stored: {len(self._configs)}.")
        return config_object

    def get_config(self, server_id: str) -> Optional[BaseMcpConfig]:
        """
        Retrieves an MCP server configuration by its unique server ID.
        Args:
            server_id: The unique ID of the MCP server configuration.
        Returns:
            The McpServerConfig object (subclass of BaseMcpConfig) if found, otherwise None.
        """
        config = self._configs.get(server_id)
        if not config:
            logger.debug(f"McpServerConfig not found for server_id: '{server_id}'.")
        return config

    def get_all_configs(self) -> List[BaseMcpConfig]:
        return list(self._configs.values())

    def clear_configs(self) -> None:
        self._configs.clear()
        logger.info("All MCP server configurations cleared from McpConfigService.")
