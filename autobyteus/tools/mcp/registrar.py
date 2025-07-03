# file: autobyteus/autobyteus/tools/mcp/registrar.py
import logging
from typing import Any, Dict, List, Optional, Union

# Import the new handler architecture components
from .call_handlers import (
    McpCallHandler,
    StdioMcpCallHandler,
    StreamableHttpMcpCallHandler,
    SseMcpCallHandler
)

# Consolidated imports from the autobyteus.autobyteus.mcp package public API
from autobyteus.tools.mcp import (
    McpConfigService,
    McpSchemaMapper,
    McpToolFactory,
    McpTransportType,
    BaseMcpConfig
)

from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.utils.singleton import SingletonMeta
from mcp import types as mcp_types


logger = logging.getLogger(__name__)

class McpToolRegistrar(metaclass=SingletonMeta):
    """
    Orchestrates the discovery of remote MCP tools and their registration
    with the AutoByteUs ToolRegistry using a handler-based architecture.
    This class is a singleton.
    """
    def __init__(self):
        """
        Initializes the McpToolRegistrar singleton.
        It retrieves singleton instances of its service dependencies and initializes
        its internal state for tracking registered tools.
        """
        self._config_service: McpConfigService = McpConfigService()
        self._tool_registry: ToolRegistry = ToolRegistry()
        
        # The handler registry maps a transport type to a reusable handler instance.
        self._handler_registry: Dict[McpTransportType, McpCallHandler] = {
            McpTransportType.STDIO: StdioMcpCallHandler(),
            McpTransportType.STREAMABLE_HTTP: StreamableHttpMcpCallHandler(),
            McpTransportType.SSE: SseMcpCallHandler(),
        }

        # Internal state to track which ToolDefinitions were registered from which server.
        self._registered_tools_by_server: Dict[str, List[ToolDefinition]] = {}
        
        logger.info(f"McpToolRegistrar initialized with {len(self._handler_registry)} call handlers.")

    async def discover_and_register_tools(self, mcp_config: Optional[Union[BaseMcpConfig, Dict[str, Any]]] = None) -> None:
        """
        Discovers tools from MCP servers and registers them.

        If `mcp_config` is provided (as a validated object or a raw dictionary),
        it discovers tools only from that specific server.
        
        If `mcp_config` is None, it discovers tools from all enabled servers
        found in the McpConfigService.
        """
        configs_to_process: List[BaseMcpConfig]
        
        if mcp_config:
            validated_config: BaseMcpConfig
            # If the user provided a raw dictionary, parse and add it via the service.
            if isinstance(mcp_config, dict):
                try:
                    # Use the new singular load_config method
                    validated_config = self._config_service.load_config(mcp_config)
                except ValueError as e:
                    logger.error(f"Failed to parse provided MCP config dictionary: {e}")
                    raise
            # If a validated object was passed, add it to the service to ensure it's known.
            elif isinstance(mcp_config, BaseMcpConfig):
                validated_config = self._config_service.add_config(mcp_config)
            else:
                raise TypeError(f"mcp_config must be a BaseMcpConfig object or a dictionary, not {type(mcp_config)}.")
            
            logger.info(f"Starting targeted MCP tool discovery for server: {validated_config.server_id}")
            # When targeting a specific server, clear only its previous registrations.
            self._registered_tools_by_server.pop(validated_config.server_id, None)
            configs_to_process = [validated_config]
        else:
            logger.info("Starting full MCP tool discovery and registration process.")
            # When doing a full scan, clear all previous registration tracking state
            self._registered_tools_by_server.clear()
            configs_to_process = self._config_service.get_all_configs()

        if not configs_to_process:
            logger.info("No MCP server configurations to process. Skipping discovery.")
            return

        schema_mapper = McpSchemaMapper()
        registered_count = 0
        for server_config in configs_to_process:
            if not server_config.enabled:
                logger.info(f"MCP server '{server_config.server_id}' is disabled. Skipping.")
                continue

            logger.info(f"Discovering tools from MCP server: '{server_config.server_id}' ({server_config.transport_type.value})")
            try:
                handler = self._handler_registry.get(server_config.transport_type)
                if not handler:
                    logger.error(f"No MCP call handler found for transport type '{server_config.transport_type.value}' on server '{server_config.server_id}'.")
                    continue

                remote_tools_result = await handler.handle_call(
                    config=server_config,
                    remote_tool_name="list_tools",
                    arguments={}
                )
                
                if not isinstance(remote_tools_result, mcp_types.ListToolsResult):
                    logger.error(f"Expected ListToolsResult from handler for 'list_tools', but got {type(remote_tools_result)}. Skipping server '{server_config.server_id}'.")
                    continue

                actual_remote_tools: list[mcp_types.Tool] = remote_tools_result.tools
                logger.info(f"Discovered {len(actual_remote_tools)} tools from server '{server_config.server_id}'.")

                for remote_tool in actual_remote_tools: 
                    try:
                        if hasattr(remote_tool, 'model_dump_json'):
                             logger.debug(f"Processing remote tool from server '{server_config.server_id}':\n{remote_tool.model_dump_json(indent=2)}")
                        
                        actual_arg_schema = schema_mapper.map_to_autobyteus_schema(remote_tool.inputSchema)
                        actual_desc = remote_tool.description
                        
                        registered_name = remote_tool.name
                        if server_config.tool_name_prefix:
                            registered_name = f"{server_config.tool_name_prefix.rstrip('_')}_{remote_tool.name}"

                        tool_factory = McpToolFactory(
                            mcp_server_config=server_config,
                            mcp_remote_tool_name=remote_tool.name,
                            mcp_call_handler=handler,
                            registered_tool_name=registered_name,
                            tool_description=actual_desc,
                            tool_argument_schema=actual_arg_schema
                        )
                        
                        tool_def = ToolDefinition(
                            name=registered_name,
                            description=actual_desc,
                            argument_schema=actual_arg_schema,
                            custom_factory=tool_factory.create_tool,
                            config_schema=None,
                            tool_class=None
                        )

                        self._tool_registry.register_tool(tool_def)
                        
                        self._registered_tools_by_server.setdefault(server_config.server_id, []).append(tool_def)
                        
                        logger.info(f"Successfully registered MCP tool '{remote_tool.name}' from server '{server_config.server_id}' as '{registered_name}'.")
                        registered_count +=1
                    except Exception as e_tool:
                        logger.error(f"Failed to process or register remote tool '{remote_tool.name}' from server '{server_config.server_id}': {e_tool}", exc_info=True)
            
            except Exception as e_server:
                logger.error(f"Failed to discover tools from MCP server '{server_config.server_id}': {e_server}", exc_info=True)
        
        logger.info(f"MCP tool discovery and registration process completed. Total tools registered: {registered_count}.")

    def get_registered_tools_for_server(self, server_id: str) -> List[ToolDefinition]:
        """
        Returns a list of ToolDefinition objects that were successfully registered 
        from a specific MCP server during the most recent discovery process.

        Args:
            server_id: The unique ID of the MCP server to query.

        Returns:
            A list of ToolDefinition objects. Returns an empty list if the server ID
            is not found or registered no tools.
        """
        return self._registered_tools_by_server.get(server_id, [])

    def get_all_registered_mcp_tools(self) -> List[ToolDefinition]:
        """
        Returns a flat list of all ToolDefinitions registered from any MCP server.
        """
        all_tools = []
        for server_tools in self._registered_tools_by_server.values():
            all_tools.extend(server_tools)
        return all_tools
