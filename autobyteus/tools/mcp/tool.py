# file: autobyteus/autobyteus/mcp/tool.py
import logging
from typing import Any, Optional, TYPE_CHECKING, Dict
import asyncio
import xml.sax.saxutils

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterType
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from .connection_manager import McpConnectionManager 

logger = logging.getLogger(__name__)

class GenericMcpTool(BaseTool):
    """
    A generic tool wrapper for executing tools on a remote MCP server.
    This tool is instantiated by a custom factory specific to a discovered
    remote MCP tool. It overrides the base class's schema generation methods
    to provide instance-specific details.
    """

    def __init__(self,
                 mcp_server_id: str,
                 mcp_remote_tool_name: str,
                 mcp_connection_manager: 'McpConnectionManager',
                 name: str, 
                 description: str,
                 argument_schema: ParameterSchema):
        """
        Initializes the GenericMcpTool instance.
        """
        super().__init__() 
        
        self._mcp_server_id = mcp_server_id
        self._mcp_remote_tool_name = mcp_remote_tool_name
        self._mcp_connection_manager = mcp_connection_manager
        
        self._instance_name = name
        self._instance_description = description
        self._instance_argument_schema = argument_schema
        
        # Override the class methods with instance-specific versions
        self.get_name = self.get_instance_name
        self.get_description = self.get_instance_description
        self.get_argument_schema = self.get_instance_argument_schema
        self.tool_usage_xml = self._instance_tool_usage_xml
        self.tool_usage_json = self._instance_tool_usage_json
        
        logger.info(f"GenericMcpTool instance created for remote tool '{mcp_remote_tool_name}' on server '{self._mcp_server_id}'. "
                    f"Registered in AutoByteUs as '{self._instance_name}'. Schema methods overridden.")

    # --- Instance-specific schema generation methods ---

    def _instance_tool_usage_xml(self) -> str:
        """Generates the XML usage string using instance-specific data."""
        name = self.get_instance_name()
        description = self.get_instance_description()
        arg_schema = self.get_instance_argument_schema()
        
        escaped_description = xml.sax.saxutils.escape(str(description)) if description is not None else ""
        command_tag = f'<command name="{name}" description="{escaped_description}">'
        xml_parts = [command_tag]

        if arg_schema and arg_schema.parameters:
            for param in arg_schema.parameters:
                arg_tag = f"    <arg name=\"{param.name}\""
                arg_tag += f" type=\"{param.param_type.value}\""
                if param.description:
                    escaped_param_desc = xml.sax.saxutils.escape(param.description)
                    arg_tag += f" description=\"{escaped_param_desc}\""
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

    def _instance_tool_usage_json(self) -> Dict[str, Any]:
        """Generates the JSON usage dictionary using instance-specific data."""
        name = self.get_instance_name()
        description = self.get_instance_description()
        arg_schema = self.get_instance_argument_schema()

        input_schema_dict = {}
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

    # --- Getters for instance-specific data ---

    def get_instance_name(self) -> str:
        return self._instance_name

    def get_instance_description(self) -> str:
        return self._instance_description

    def get_instance_argument_schema(self) -> ParameterSchema:
        return self._instance_argument_schema

    # --- Base class methods that are NOT overridden at instance level ---

    @classmethod
    def get_name(cls) -> str:
        return "GenericMcpTool" 

    @classmethod
    def get_description(cls) -> str:
        return "A generic wrapper for executing tools on a remote MCP server. Specifics are instance-based."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        return None 

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> Any:
        """
        Executes the remote MCP tool call.
        """
        # self.get_name() will now call the instance's lambda and return the specific name
        tool_name_for_log = self.get_instance_name()
        logger.info(f"GenericMcpTool '{tool_name_for_log}': Executing remote tool '{self._mcp_remote_tool_name}' "
                    f"on server '{self._mcp_server_id}' with args: {kwargs}")
        
        if not self._mcp_connection_manager: 
             logger.error(f"GenericMcpTool '{tool_name_for_log}': McpConnectionManager is not set. Cannot execute.")
             raise RuntimeError("McpConnectionManager not available in GenericMcpTool instance.")

        try:
            session = await self._mcp_connection_manager.get_session(self._mcp_server_id)
        except Exception as e:
            logger.error(f"GenericMcpTool '{tool_name_for_log}': Failed to get MCP session for server '{self._mcp_server_id}': {e}", exc_info=True)
            raise RuntimeError(f"Failed to acquire MCP session for server '{self._mcp_server_id}': {e}") from e

        try:
            result = await session.call_tool(self._mcp_remote_tool_name, kwargs)
            logger.info(f"GenericMcpTool '{tool_name_for_log}': Remote tool '{self._mcp_remote_tool_name}' executed successfully. Result preview: {str(result)[:100]}...")
            return result
        except Exception as e:
            logger.error(f"GenericMcpTool '{tool_name_for_log}': Error calling remote tool '{self._mcp_remote_tool_name}' on server '{self._mcp_server_id}': {e}", exc_info=True)
            raise RuntimeError(f"Error calling remote MCP tool '{self._mcp_remote_tool_name}': {e}") from e
