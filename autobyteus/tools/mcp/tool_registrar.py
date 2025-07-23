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

    async def discover_and_register_tools(self, mcp_config: Optional[Union[BaseMcpConfig, Dict[str, Any]]] = None) -> List[ToolDefinition]:
        """
        Discovers tools from MCP servers and registers them.
        """
        configs_to_process: List[BaseMcpConfig]
        
        if mcp_config:
            validated_config: BaseMcpConfig
            if isinstance(mcp_config, dict):
                try:
                    validated_config = self._config_service.load_config(mcp_config)
                except ValueError as e:
                    logger.error(f"Failed to parse provided MCP config dictionary: {e}")
                    raise
            elif isinstance(mcp_config, BaseMcpConfig):
                validated_config = self._config_service.add_config(mcp_config)
            else:
                raise TypeError(f"mcp_config must be a BaseMcpConfig object or a dictionary, not {type(mcp_config)}.")
            
            logger.info(f"Starting targeted MCP tool discovery for server: {validated_config.server_id}")
            self.unregister_tools_from_server(validated_config.server_id)
            configs_to_process = [validated_config]
        else:
            logger.info("Starting full MCP tool discovery. Unregistering all existing MCP tools first.")
            all_server_ids = list(self._registered_tools_by_server.keys())
            for server_id in all_server_ids:
                self.unregister_tools_from_server(server_id)
            self._registered_tools_by_server.clear()
            configs_to_process = self._config_service.get_all_configs()

        if not configs_to_process:
            logger.info("No MCP server configurations to process. Skipping discovery.")
            return []

        schema_mapper = McpSchemaMapper()
        registered_tool_definitions: List[ToolDefinition] = []
        for server_config in configs_to_process:
            if not server_config.enabled:
                logger.info(f"MCP server '{server_config.server_id}' is disabled. Skipping.")
                continue

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
        
        logger.info(f"MCP tool discovery and registration process completed. Total tools registered: {len(registered_tool_definitions)}.")
        return registered_tool_definitions

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
