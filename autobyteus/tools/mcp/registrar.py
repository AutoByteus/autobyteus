# file: autobyteus/autobyteus/mcp/registrar.py
import logging
import asyncio 
from typing import Callable, Optional, Any, Dict

# Consolidated imports from the autobyteus.autobyteus.mcp package public API
from autobyteus.tools.mcp import (
    McpConfigService,
    McpConnectionManager,
    McpSchemaMapper,
    GenericMcpTool # BaseMcpConfig and its subclasses are used via McpConfigService
)

from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterType 

from mcp import types as mcp_types


logger = logging.getLogger(__name__)

class McpToolRegistrar:
    """
    Orchestrates the discovery of remote MCP tools and their registration
    with the AutoByteUs ToolRegistry using custom factories.
    """
    def __init__(self,
                 config_service: McpConfigService,
                 conn_manager: McpConnectionManager,
                 schema_mapper: McpSchemaMapper,
                 tool_registry: ToolRegistry):
        if not isinstance(config_service, McpConfigService):
            raise TypeError("config_service must be an McpConfigService instance.")
        if not isinstance(conn_manager, McpConnectionManager):
            raise TypeError("conn_manager must be an McpConnectionManager instance.")
        if not isinstance(schema_mapper, McpSchemaMapper):
            raise TypeError("schema_mapper must be an McpSchemaMapper instance.")
        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError("tool_registry must be a ToolRegistry instance.")

        self._config_service = config_service
        self._conn_manager = conn_manager
        self._schema_mapper = schema_mapper
        self._tool_registry = tool_registry
        logger.info("McpToolRegistrar initialized.")

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
        for server_config in all_server_configs: # server_config is a BaseMcpConfig subclass instance
            if not server_config.enabled:
                logger.info(f"MCP server '{server_config.server_id}' is disabled. Skipping.") # RENAMED
                continue

            logger.info(f"Discovering tools from MCP server: '{server_config.server_id}' ({server_config.transport_type.value})") # RENAMED
            try:
                # server_config.server_id is the correct identifier for get_session
                session = await self._conn_manager.get_session(server_config.server_id) # RENAMED
                
                remote_tools_result: mcp_types.ListToolsResult 
                if hasattr(session, 'list_tools') and asyncio.iscoroutinefunction(session.list_tools):
                    remote_tools_result = await session.list_tools()
                elif hasattr(session, 'list_tools'): 
                    remote_tools_result = session.list_tools() # type: ignore
                else:
                    logger.error(f"ClientSession for server '{server_config.server_id}' does not have a 'list_tools' method.") # RENAMED
                    continue
                
                actual_remote_tools: list[mcp_types.Tool] = []
                if remote_tools_result and hasattr(remote_tools_result, 'tools'):
                    actual_remote_tools = remote_tools_result.tools
                else:
                    logger.warning(f"ListToolsResult from server '{server_config.server_id}' is None or has no 'tools' attribute. Result: {remote_tools_result}") # RENAMED

                logger.info(f"Discovered {len(actual_remote_tools)} tools from server '{server_config.server_id}'.") # RENAMED

                for remote_tool in actual_remote_tools: 
                    try:
                        logger.debug(f"Processing remote tool '{remote_tool.name}' from server '{server_config.server_id}'.") # RENAMED
                        
                        actual_arg_schema = self._schema_mapper.map_to_autobyteus_schema(remote_tool.inputSchema)
                        actual_desc = remote_tool.description
                        
                        registered_name = remote_tool.name
                        if server_config.tool_name_prefix:
                            registered_name = f"{server_config.tool_name_prefix.rstrip('_')}_{remote_tool.name}"

                        factory_func = self._create_factory_for_tool(
                            mcp_server_id=server_config.server_id, # RENAMED
                            mcp_remote_tool_name=remote_tool.name,
                            connection_manager=self._conn_manager,
                            registered_tool_name=registered_name,
                            tool_description=actual_desc,
                            tool_argument_schema=actual_arg_schema
                        )
                        
                        usage_xml = self._generate_usage_xml(registered_name, actual_desc, actual_arg_schema)
                        usage_json_dict = self._generate_usage_json(registered_name, actual_desc, actual_arg_schema)

                        tool_def = ToolDefinition(
                            name=registered_name,
                            description=actual_desc,
                            argument_schema=actual_arg_schema,
                            usage_xml=usage_xml,
                            usage_json_dict=usage_json_dict,
                            tool_class=GenericMcpTool, 
                            custom_factory=factory_func, 
                            config_schema=None 
                        )

                        self._tool_registry.register_tool(tool_def)
                        logger.info(f"Successfully registered MCP tool '{remote_tool.name}' from server '{server_config.server_id}' as '{registered_name}'.") # RENAMED
                        registered_count +=1
                    except Exception as e_tool:
                        logger.error(f"Failed to process or register remote tool '{remote_tool.name}' from server '{server_config.server_id}': {e_tool}", exc_info=True) # RENAMED
            
            except Exception as e_server:
                logger.error(f"Failed to discover tools from MCP server '{server_config.server_id}': {e_server}", exc_info=True) # RENAMED
        
        logger.info(f"MCP tool discovery and registration process completed. Total tools registered: {registered_count}.")

    def _create_factory_for_tool(self,
                                 mcp_server_id: str, # RENAMED from mcp_server_name
                                 mcp_remote_tool_name: str,
                                 connection_manager: McpConnectionManager,
                                 registered_tool_name: str,
                                 tool_description: str,
                                 tool_argument_schema: ParameterSchema
                                 ) -> Callable[[Optional[ToolConfig]], BaseTool]:
        def mcp_tool_factory(tool_config: Optional[ToolConfig] = None) -> GenericMcpTool:
            if tool_config and tool_config.params:
                 logger.debug(f"McpToolFactory for remote '{mcp_remote_tool_name}' on server '{mcp_server_id}' received ToolConfig with params: {list(tool_config.params.keys())}") # RENAMED

            return GenericMcpTool(
                mcp_server_id=mcp_server_id, # This is already named mcp_server_id in GenericMcpTool constructor
                mcp_remote_tool_name=mcp_remote_tool_name,
                mcp_connection_manager=connection_manager,
                name=registered_tool_name,
                description=tool_description,
                argument_schema=tool_argument_schema
            )
            
        logger.debug(f"Created factory for MCP tool '{mcp_remote_tool_name}' (server '{mcp_server_id}') to be registered as '{registered_tool_name}'.") # RENAMED
        return mcp_tool_factory

    def _generate_usage_xml(self, name: str, description: str, arg_schema: Optional[ParameterSchema]) -> str:
        import xml.sax.saxutils

        xml_parts = [f"<command name=\"{name}\">"]
        escaped_tool_description = xml.sax.saxutils.escape(str(description)) if description is not None else "No description provided."
        xml_parts.append(f"    <!-- Description: {escaped_tool_description} -->")
        
        if arg_schema and arg_schema.parameters:
            for param in arg_schema.parameters: 
                arg_tag = f"    <arg name=\"{param.name}\""
                arg_tag += f" type=\"{param.param_type.value}\""
                if param.description:
                    escaped_description = xml.sax.saxutils.escape(param.description)
                    arg_tag += f" description=\"{escaped_description}\""
                arg_tag += f" required=\"{'true' if param.required else 'false'}\""

                if param.default_value is not None:
                    arg_tag += f" default=\"{xml.sax.saxutils.escape(str(param.default_value))}\""
                if param.param_type == ParameterType.ENUM and param.enum_values:
                    escaped_enum_values = [xml.sax.saxutils.escape(ev) for ev in param.enum_values]
                    arg_tag += f" enum_values=\"{','.join(escaped_enum_values)}\""
                
                arg_tag += " />"
                xml_parts.append(arg_tag)
        else:
            xml_parts.append("    <!-- This tool takes no arguments -->")
            
        xml_parts.append("</command>")
        return "\n".join(xml_parts)

    def _generate_usage_json(self, name: str, description: str, arg_schema: Optional[ParameterSchema]) -> Dict[str, Any]:
        input_schema_dict: Dict[str, Any]
        if arg_schema:
            input_schema_dict = arg_schema.to_json_schema_dict()
        else: 
            input_schema_dict = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
        return {
            "name": name,
            "description": str(description) if description is not None else "No description provided.",
            "inputSchema": input_schema_dict,
        }
