# file: autobyteus/autobyteus/tools/mcp/registrar.py
import logging
from typing import Dict

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
    McpTransportType
)

from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from mcp import types as mcp_types


logger = logging.getLogger(__name__)

class McpToolRegistrar:
    """
    Orchestrates the discovery of remote MCP tools and their registration
    with the AutoByteUs ToolRegistry using a handler-based architecture.
    """
    def __init__(self,
                 config_service: McpConfigService,
                 schema_mapper: McpSchemaMapper,
                 tool_registry: ToolRegistry):
        if not isinstance(config_service, McpConfigService):
            raise TypeError("config_service must be an McpConfigService instance.")
        if not isinstance(schema_mapper, McpSchemaMapper):
            raise TypeError("schema_mapper must be an McpSchemaMapper instance.")
        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError("tool_registry must be a ToolRegistry instance.")

        self._config_service = config_service
        self._schema_mapper = schema_mapper
        self._tool_registry = tool_registry
        
        # The handler registry maps a transport type to a reusable handler instance.
        self._handler_registry: Dict[McpTransportType, McpCallHandler] = {
            McpTransportType.STDIO: StdioMcpCallHandler(),
            McpTransportType.STREAMABLE_HTTP: StreamableHttpMcpCallHandler(),
            McpTransportType.SSE: SseMcpCallHandler(),
        }
        
        logger.info(f"McpToolRegistrar initialized with {len(self._handler_registry)} call handlers.")

    async def discover_and_register_tools(self) -> None:
        """
        Discovers tools from all enabled MCP servers and registers them.
        """
        logger.info("Starting MCP tool discovery and registration process.")
        all_server_configs = self._config_service.get_all_configs() 
        if not all_server_configs:
            logger.info("No MCP server configurations found. Skipping discovery.")
            return

        registered_count = 0
        for server_config in all_server_configs:
            if not server_config.enabled:
                logger.info(f"MCP server '{server_config.server_id}' is disabled. Skipping.")
                continue

            logger.info(f"Discovering tools from MCP server: '{server_config.server_id}' ({server_config.transport_type.value})")
            try:
                # Get the correct handler for this server's transport type.
                handler = self._handler_registry.get(server_config.transport_type)
                if not handler:
                    logger.error(f"No MCP call handler found for transport type '{server_config.transport_type.value}' on server '{server_config.server_id}'.")
                    continue

                # Use the handler to call the special 'list_tools' method.
                # The registrar does not need to know how this is done; it's encapsulated in the handler.
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
                        
                        actual_arg_schema = self._schema_mapper.map_to_autobyteus_schema(remote_tool.inputSchema)
                        actual_desc = remote_tool.description
                        
                        registered_name = remote_tool.name
                        if server_config.tool_name_prefix:
                            registered_name = f"{server_config.tool_name_prefix.rstrip('_')}_{remote_tool.name}"

                        # Create the tool factory, injecting the server config and the correct handler.
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
                        logger.info(f"Successfully registered MCP tool '{remote_tool.name}' from server '{server_config.server_id}' as '{registered_name}'.")
                        registered_count +=1
                    except Exception as e_tool:
                        logger.error(f"Failed to process or register remote tool '{remote_tool.name}' from server '{server_config.server_id}': {e_tool}", exc_info=True)
            
            except Exception as e_server:
                logger.error(f"Failed to discover tools from MCP server '{server_config.server_id}': {e_server}", exc_info=True)
        
        logger.info(f"MCP tool discovery and registration process completed. Total tools registered: {registered_count}.")
