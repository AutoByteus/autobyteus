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

    @staticmethod
    def _parse_transport_type(type_str: str, server_identifier: str) -> McpTransportType:
        """Parses string to McpTransportType enum."""
        try:
            return McpTransportType(type_str.lower())
        except ValueError:
            valid_types = [t.value for t in McpTransportType]
            raise ValueError(
                f"Invalid 'transport_type' string '{type_str}' for server '{server_identifier}'. "
                f"Valid types are: {valid_types}."
            )

    @staticmethod
    def _create_specific_config(server_id: str, transport_type: McpTransportType, config_data: Dict[str, Any]) -> BaseMcpConfig:
        """
        Creates a specific McpServerConfig (Stdio, Sse, StreamableHttp) based on transport_type.
        The 'server_id' is injected.
        Parameters from nested structures like 'stdio_params' are un-nested.
        """
        constructor_params = {'server_id': server_id}
        
        for base_key in ['enabled', 'tool_name_prefix']:
            if base_key in config_data:
                constructor_params[base_key] = config_data[base_key]

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
            constructor_params.update(specific_params_dict)
        
        constructor_params.pop(transport_specific_params_key_map.get(McpTransportType.STDIO), None)
        constructor_params.pop(transport_specific_params_key_map.get(McpTransportType.SSE), None)
        constructor_params.pop(transport_specific_params_key_map.get(McpTransportType.STREAMABLE_HTTP), None)
        constructor_params.pop('transport_type', None)
        
        other_top_level_keys_to_copy = {
            k: v for k, v in config_data.items() 
            if k not in ['enabled', 'tool_name_prefix', 'transport_type'] and k not in transport_specific_params_key_map.values()
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
                raise ValueError(f"Unsupported McpTransportType '{transport_type}' for server '{server_id}'.")
        except TypeError as e:
            logger.error(f"TypeError creating config for server '{server_id}' with transport '{transport_type}'. "
                         f"Params: {constructor_params}. Error: {e}", exc_info=True)
            raise ValueError(f"Failed to create config for server '{server_id}' due to incompatible parameters for {transport_type.name} config: {e}")

    @staticmethod
    def parse_mcp_config_dict(config_dict: Dict[str, Any]) -> BaseMcpConfig:
        """
        Parses a dictionary representing a single MCP server configuration into a
        validated BaseMcpConfig dataclass object.
        The dictionary is expected to have a single top-level key which is the server_id.
        """
        if not isinstance(config_dict, dict) or len(config_dict) != 1:
            raise ValueError("Input must be a dictionary with a single top-level key representing the server_id.")

        server_id = next(iter(config_dict))
        config_data = config_dict[server_id]

        if not isinstance(config_data, dict):
            raise ValueError(f"Configuration for server '{server_id}' must be a dictionary.")

        transport_type_str = config_data.get('transport_type')
        if not transport_type_str:
            raise ValueError(f"Config data for server '{server_id}' is missing 'transport_type' field.")

        transport_type = McpConfigService._parse_transport_type(transport_type_str, server_id)
        return McpConfigService._create_specific_config(server_id, transport_type, config_data)

    def add_config(self, config_object: BaseMcpConfig) -> BaseMcpConfig:
        """Adds or updates a single, pre-instantiated MCP server configuration object."""
        if not isinstance(config_object, BaseMcpConfig):
            raise TypeError(f"Unsupported input type for add_config: {type(config_object)}. "
                            "Expected a BaseMcpConfig subclass object (e.g., StdioMcpServerConfig).")

        if config_object.server_id in self._configs:
            logger.warning(f"Overwriting existing MCP config with server_id '{config_object.server_id}'.")
        
        self._configs[config_object.server_id] = config_object
        logger.info(f"Successfully added/updated {type(config_object).__name__} for server_id '{config_object.server_id}'. "
                    f"Total unique configs stored: {len(self._configs)}.")
        return config_object

    def load_config(self, config_dict: Dict[str, Any]) -> BaseMcpConfig:
        """
        Parses a single raw configuration dictionary and adds it to the service.

        Args:
            config_dict: A dictionary representing a single server config,
                         with the server_id as the top-level key.
        
        Returns:
            The successfully parsed and added McpServerConfig object.
        """
        config_object = self.parse_mcp_config_dict(config_dict)
        return self.add_config(config_object)


    def load_configs(self, source: Union[str, List[Dict[str, Any]], Dict[str, Any]]) -> List[BaseMcpConfig]:
        """
        Loads multiple MCP configurations from a source, parsing and adding them.
        This will overwrite any existing configurations with the same server_id.

        Args:
            source: The data source. Can be:
                1. A file path (str) to a JSON file.
                2. A list of MCP server configuration dictionaries.
                3. A dictionary of configurations, keyed by server_id.
        
        Returns:
            A list of the successfully added McpServerConfig objects.
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
                return self.load_configs(json_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in MCP configuration file {source}: {e}") from e
            except Exception as e:
                raise ValueError(f"Could not read MCP configuration file {source}: {e}") from e

        elif isinstance(source, list):
            for i, config_item_dict in enumerate(source):
                if not isinstance(config_item_dict, dict):
                    raise ValueError(f"Item at index {i} in source list is not a dictionary.")
                
                server_id = config_item_dict.get('server_id')
                if not server_id:
                     raise ValueError(f"Item at index {i} in source list is missing 'server_id' field.")
                
                try:
                    # A list item is a single config, but doesn't have the server_id as the key,
                    # so we wrap it to use the parser.
                    config_obj = McpConfigService.parse_mcp_config_dict({server_id: config_item_dict})
                    self.add_config(config_obj)
                    loaded_mcp_configs.append(config_obj)
                except ValueError as e:
                    logger.error(f"Invalid MCP configuration for list item at index {i}: {e}")
                    raise
        
        elif isinstance(source, dict):
            logger.info("Loading MCP server configurations from a dictionary of configs (keyed by server_id).")
            for server_id, config_data in source.items():
                if not isinstance(config_data, dict):
                        raise ValueError(f"Configuration for server_id '{server_id}' must be a dictionary.")

                try:
                    config_obj = McpConfigService.parse_mcp_config_dict({server_id: config_data})
                    self.add_config(config_obj)
                    loaded_mcp_configs.append(config_obj)
                except ValueError as e:
                    logger.error(f"Invalid MCP configuration for server_id '{server_id}': {e}")
                    raise
        else:
            raise TypeError(f"Unsupported source type for load_configs: {type(source)}. "
                            "Expected file path, list of dicts, or dict of dicts.")

        logger.info(f"McpConfigService load_configs completed. {len(loaded_mcp_configs)} new configurations processed. "
                    f"Total unique configs stored: {len(self._configs)}.")
        return loaded_mcp_configs

    def get_config(self, server_id: str) -> Optional[BaseMcpConfig]:
        """Retrieves an MCP server configuration by its unique server ID."""
        return self._configs.get(server_id)

    def get_all_configs(self) -> List[BaseMcpConfig]:
        return list(self._configs.values())

    def remove_config(self, server_id: str) -> bool:
        """
        Removes an MCP server configuration by its unique server ID.

        Args:
            server_id: The unique ID of the MCP server configuration to remove.

        Returns:
            True if a configuration was found and removed, False otherwise.
        """
        if server_id in self._configs:
            del self._configs[server_id]
            logger.info(f"Successfully removed MCP config for server_id '{server_id}'.")
            return True
        logger.warning(f"Attempted to remove MCP config for server_id '{server_id}', but it was not found.")
        return False

    def clear_configs(self) -> None:
        self._configs.clear()
        logger.info("All MCP server configurations cleared from McpConfigService.")
