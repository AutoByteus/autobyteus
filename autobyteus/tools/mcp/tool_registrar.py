# file: autobyteus/autobyteus/tools/mcp/tool_registrar.py
import logging
from typing import Any, Dict, List, Optional, Union

# Consolidated imports from the autobyteus.autobyteus.mcp package public API
from .config_service import McpConfigService
from .factory import McpToolFactory
from .schema_mapper import McpSchemaMapper
from .server_instance_manager import McpServerInstanceManager
from .types import BaseMcpConfig
from .server import BaseManagedMcpServer

from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.singleton import SingletonMeta
from mcp import types as mcp_types


logger = logging.getLogger(__name__)

class McpToolRegistrar(metaclass=SingletonMeta):
    """
    Orchestrates the discovery of remote MCP tools and their registration
    with the AutoByteUs ToolRegistry.
    """
    def __init__(self):
        """
        Initializes the McpToolRegistrar singleton.
        """
        self._config_service: McpConfigService = McpConfigService()
        self._tool_registry: ToolRegistry = ToolRegistry()
        self._instance_manager: McpServerInstanceManager = McpServerInstanceManager()
        self._registered_tools_by_server: Dict[str, List[ToolDefinition]] = {}
        logger.info("McpToolRegistrar initialized.")

    async def _fetch_tools_from_server(self, server_config: BaseMcpConfig) -> List[mcp_types.Tool]:
        """
        Uses the instance manager to get a temporary, managed session for discovery.
        """
        async with self._instance_manager.managed_discovery_session(server_config) as discovery_server:
            # The context manager guarantees the server is connected and will be closed.
            remote_tools = await discovery_server.list_remote_tools()
            return remote_tools

    def _create_tool_definition_from_remote(
        self,
        remote_tool: mcp_types.Tool,
        server_config: BaseMcpConfig,
        schema_mapper: McpSchemaMapper
    ) -> ToolDefinition:
        """
        Maps a single remote tool from an MCP server to an AutoByteUs ToolDefinition.
        """
        actual_arg_schema = schema_mapper.map_to_autobyteus_schema(remote_tool.inputSchema)
        actual_desc = remote_tool.description
        
        registered_name = remote_tool.name
        if server_config.tool_name_prefix:
            registered_name = f"{server_config.tool_name_prefix.rstrip('_')}_{remote_tool.name}"

        tool_factory = McpToolFactory(
            server_id=server_config.server_id,
            remote_tool_name=remote_tool.name,
            registered_tool_name=registered_name,
            tool_description=actual_desc,
            tool_argument_schema=actual_arg_schema
        )
        
        return ToolDefinition(
            name=registered_name,
            description=actual_desc,
            argument_schema=actual_arg_schema,
            origin=ToolOrigin.MCP,
            category=server_config.server_id, # Use server_id as the category
            metadata={"mcp_server_id": server_config.server_id}, # Store origin in generic metadata
            custom_factory=tool_factory.create_tool,
            config_schema=None,
            tool_class=None
        )

    async def _discover_and_register_from_config(self, server_config: BaseMcpConfig, schema_mapper: McpSchemaMapper) -> List[ToolDefinition]:
        """
        Performs the core discovery and registration logic for a single server configuration.
        This method does NOT handle un-registration of existing tools.
        """
        registered_tool_definitions: List[ToolDefinition] = []
        if not server_config.enabled:
            logger.info(f"MCP server '{server_config.server_id}' is disabled. Skipping.")
            return registered_tool_definitions

        logger.info(f"Discovering tools from MCP server: '{server_config.server_id}'")
        
        try:
            remote_tools = await self._fetch_tools_from_server(server_config)
            logger.info(f"Discovered {len(remote_tools)} tools from server '{server_config.server_id}'.")

            for remote_tool in remote_tools:
                try:
                    tool_def = self._create_tool_definition_from_remote(remote_tool, server_config, schema_mapper)
                    self._tool_registry.register_tool(tool_def)
                    self._registered_tools_by_server.setdefault(server_config.server_id, []).append(tool_def)
                    registered_tool_definitions.append(tool_def)
                except Exception as e_tool:
                    logger.error(f"Failed to process or register remote tool '{remote_tool.name}': {e_tool}", exc_info=True)
        
        except Exception as e_server:
            logger.error(f"Failed to discover tools from MCP server '{server_config.server_id}': {e_server}", exc_info=True)
            # Re-raise to signal failure to the caller
            raise
        
        return registered_tool_definitions

    async def register_server(self, config_object: BaseMcpConfig) -> List[ToolDefinition]:
        """
        Discovers and registers tools from a single MCP server using a validated
        config object. This will overwrite any existing tools from that server.

        Args:
            config_object: A pre-instantiated and validated BaseMcpConfig object.

        Returns:
            A list of the successfully registered ToolDefinition objects from this server.
        """
        if not isinstance(config_object, BaseMcpConfig):
            raise TypeError(f"config_object must be a BaseMcpConfig object, not {type(config_object)}.")

        # Add/update the config in the service
        self._config_service.add_config(config_object)

        logger.info(f"Starting targeted MCP tool registration for server: {config_object.server_id}")
        
        # Unregister existing tools for this specific server before re-registering
        self.unregister_tools_from_server(config_object.server_id)
        
        schema_mapper = McpSchemaMapper()
        
        return await self._discover_and_register_from_config(config_object, schema_mapper)

    async def load_and_register_server(self, config_dict: Dict[str, Any]) -> List[ToolDefinition]:
        """
        Loads a server configuration from a dictionary, then discovers and registers its tools.
        This is a convenience method that wraps the parsing and registration process.

        Args:
            config_dict: The raw dictionary configuration for a single MCP server.

        Returns:
            A list of the successfully registered ToolDefinition objects from this server.
        """
        logger.debug(f"Attempting to load and register server from dictionary: {config_dict.get(next(iter(config_dict), 'unknown'))}")
        try:
            validated_config = self._config_service.load_config_from_dict(config_dict)
        except ValueError as e:
            logger.error(f"Failed to parse provided MCP config dictionary: {e}")
            raise
        
        return await self.register_server(validated_config)

    async def reload_all_mcp_tools(self) -> List[ToolDefinition]:
        """
        Performs a full refresh of tools from ALL MCP servers currently configured
        in the McpConfigService. This first unregisters all previously registered
        MCP tools, then re-discovers and re-registers them. This process is resilient
        to failures from individual servers.

        Returns:
            A list of all successfully registered ToolDefinition objects.
        """
        logger.info("Reloading all MCP tools. Unregistering existing MCP tools first.")
        
        # Unregister all previously known MCP tools
        all_server_ids = list(self._registered_tools_by_server.keys())
        for server_id in all_server_ids:
            self.unregister_tools_from_server(server_id)
        
        configs_to_process = self._config_service.get_all_configs()
        if not configs_to_process:
            logger.info("No MCP server configurations to process. Skipping reload.")
            return []

        schema_mapper = McpSchemaMapper()
        all_registered_definitions: List[ToolDefinition] = []
        
        for server_config in configs_to_process:
            try:
                newly_registered = await self._discover_and_register_from_config(server_config, schema_mapper)
                all_registered_definitions.extend(newly_registered)
            except Exception as e:
                # Log the error but continue to the next server. This makes the process resilient.
                # exc_info is False because the inner method already logged the full stack trace.
                logger.error(f"Failed to complete discovery for server '{server_config.server_id}', it will be skipped. Error: {e}", exc_info=False)

        logger.info(f"Finished reloading all MCP tools. Total tools registered: {len(all_registered_definitions)}.")
        return all_registered_definitions

    async def list_remote_tools(self, mcp_config: Union[BaseMcpConfig, Dict[str, Any]]) -> List[ToolDefinition]:
        validated_config: BaseMcpConfig
        if isinstance(mcp_config, dict):
            validated_config = McpConfigService.parse_mcp_config_dict(mcp_config)
        elif isinstance(mcp_config, BaseMcpConfig):
            validated_config = mcp_config
        else:
            raise TypeError(f"mcp_config must be a BaseMcpConfig object or a dictionary, not {type(mcp_config)}.")
        
        logger.info(f"Previewing tools from MCP server: '{validated_config.server_id}'")
        schema_mapper = McpSchemaMapper()
        tool_definitions: List[ToolDefinition] = []

        try:
            remote_tools = await self._fetch_tools_from_server(validated_config)
            logger.info(f"Discovered {len(remote_tools)} tools from server '{validated_config.server_id}' for preview.")
            for remote_tool in remote_tools:
                tool_def = self._create_tool_definition_from_remote(remote_tool, validated_config, schema_mapper)
                tool_definitions.append(tool_def)
        except Exception as e_server:
            logger.error(f"Failed to discover tools for preview from MCP server '{validated_config.server_id}': {e_server}", exc_info=True)
            raise
            
        logger.info(f"MCP tool preview completed. Found {len(tool_definitions)} tools.")
        return tool_definitions
    
    def unregister_tools_from_server(self, server_id: str) -> bool:
        if not self.is_server_registered(server_id):
            return False
        tools_to_unregister = self._registered_tools_by_server.pop(server_id, [])
        for tool_def in tools_to_unregister:
            self._tool_registry.unregister_tool(tool_def.name)
        return True
        
    def is_server_registered(self, server_id: str) -> bool:
        return server_id in self._registered_tools_by_server
