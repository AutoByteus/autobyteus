# file: autobyteus/autobyteus/tools/mcp_remote_tool.py
import logging
import json
import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType

# Conditional import for mcp package
try:
    import mcp
except ImportError: # pragma: no cover
    mcp = None 
    logging.getLogger(__name__).warning(
        "MCP package not found. McpRemoteTool will not be usable. "
        "Please install 'mcp' if you intend to use this tool."
    )


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class McpRemoteTool(BaseTool):
    """
    A tool that executes remote tool calls on an MCP (Model Context Protocol) server.
    It acts as a proxy to tools available on an MCP server.
    """
    def __init__(self, config: Optional[ToolConfig] = None):
        """
        Initializes the McpRemoteTool.
        Configuration for MCP host and port is expected via ToolConfig.

        Args:
            config: Optional ToolConfig providing 'mcp_host' and 'mcp_port'.
        """
        super().__init__()
        self.connection_params: Dict[str, Any] = {}
        
        if config:
            host = config.get("mcp_host")
            port = config.get("mcp_port")
            if host and isinstance(host, str) and port and isinstance(port, int):
                self.connection_params = {"host": host, "port": port}
            else:
                logger.warning(
                    f"McpRemoteTool '{self.get_name()}' received incomplete or invalid config. "
                    f"Expected 'mcp_host' (str) and 'mcp_port' (int). Got host: {host} (type {type(host)}), port: {port} (type {type(port)})."
                )
        
        if not self.connection_params:
            logger.error(
                f"McpRemoteTool '{self.get_name()}' initialized without valid connection_params (mcp_host, mcp_port). "
                "MCP calls will fail. Please provide configuration."
            )
        else:
            logger.debug(f"McpRemoteTool initialized with name '{self.get_name()}' and connection_params: {self.connection_params}")

    @classmethod
    def get_name(cls) -> str:
        return "McpRemoteTool" # Explicitly define the registration name

    @classmethod
    def get_config_schema(cls) -> ToolConfigSchema:
        """Defines the configuration parameters for this tool."""
        schema = ToolConfigSchema()
        schema.add_parameter(ToolConfigParameter(
            name="mcp_host", 
            param_type=ParameterType.STRING, 
            description="Hostname or IP address of the MCP server.", 
            required=True
        ))
        schema.add_parameter(ToolConfigParameter(
            name="mcp_port", 
            param_type=ParameterType.INTEGER, 
            description="Port number of the MCP server.", 
            required=True,
            min_value=1,
            max_value=65535
        ))
        return schema

    @classmethod
    def tool_usage_xml(cls) -> str:
        """Describes how to use this tool to call a remote MCP tool."""
        return f'''{cls.get_name()}: Executes a tool call on a remote MCP server.
    Usage:
    <command name="{cls.get_name()}">
      <arg name="tool_name">name_of_tool_on_mcp_server</arg>
      <arg name="params_json_str">{{ ... JSON string of parameters for the remote tool ... }}</arg> <!-- Optional -->
    </command>
    Example:
    <command name="{cls.get_name()}">
      <arg name="tool_name">perform_complex_analysis</arg>
      <arg name="params_json_str">{{"input_data": "some_value", "threshold": 0.5}}</arg>
    </command>
    Note: The {cls.get_name()} itself must be configured with the MCP server's host and port during its initial setup by the system.
    The 'params_json_str' argument should be a valid JSON string representing a dictionary of arguments for the remote tool.
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        """
        Executes the remote tool call on the MCP server.

        Args:
            context: The AgentContext of the calling agent.
            **kwargs: Arguments for this tool. Expected:
                      'tool_name': Name of the tool to call on the MCP server.
                      'params_json_str': Optional JSON string of parameters for the remote tool.

        Returns:
            The result of the remote tool execution.

        Raises:
            ValueError: If arguments are invalid (e.g., missing 'tool_name', invalid 'params_json_str').
            RuntimeError: If MCP server connection or tool execution fails, or if mcp package is not installed.
        """
        if mcp is None:
            raise RuntimeError(f"McpRemoteTool '{self.get_name()}' cannot execute because the 'mcp' package is not installed.")

        remote_tool_name = kwargs.get('tool_name')
        if not remote_tool_name or not isinstance(remote_tool_name, str):
            raise ValueError(f"McpRemoteTool '{self.get_name()}' requires 'tool_name' (string) argument for the remote MCP tool.")
        
        params_json_str = kwargs.get('params_json_str')
        remote_params: Dict[str, Any] = {}
        if params_json_str:
            if not isinstance(params_json_str, str):
                raise ValueError("'params_json_str' must be a string if provided.")
            try:
                remote_params = json.loads(params_json_str)
                if not isinstance(remote_params, dict): # Ensure the JSON string decodes to a dictionary
                    raise ValueError("Decoded 'params_json_str' is not a dictionary.")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format in 'params_json_str': {e}")
        
        agent_id = context.agent_id # Or self.agent_id, which should be set by BaseTool.execute
        logger.info(
            f"Agent '{agent_id}' executing McpRemoteTool '{self.get_name()}' -> "
            f"Remote MCP tool: '{remote_tool_name}', Params: {remote_params}"
        )

        if not self.connection_params or not self.connection_params.get("host") or not self.connection_params.get("port"):
            err_msg = (
                f"McpRemoteTool '{self.get_name()}' used by agent '{agent_id}' is not configured "
                "with valid connection parameters (mcp_host, mcp_port)."
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        def mcp_sync_call():
            # Assuming mcp.stdio_client might take host and port if dict form is problematic
            # Or if it strictly needs a dict:
            # client = mcp.stdio_client(self.connection_params)
            client = mcp.stdio_client(host=self.connection_params['host'], port=self.connection_params['port'])
            logger.debug(f"Agent '{agent_id}': MCP client created for {self.connection_params['host']}:{self.connection_params['port']}")
            
            session = client.ClientSession()
            logger.debug(f"Agent '{agent_id}': MCP client session created for remote tool '{remote_tool_name}'")
            
            session.initialize()
            logger.debug(f"Agent '{agent_id}': MCP session initialized for remote tool '{remote_tool_name}'")
            
            mcp_result = session.call_tool(remote_tool_name, remote_params)
            logger.info(f"Agent '{agent_id}': Successfully executed remote MCP tool '{remote_tool_name}'.")
            return mcp_result

        try:
            result = await asyncio.to_thread(mcp_sync_call)
            return result
        except Exception as e:
            logger.error(
                f"Agent '{agent_id}': Failed to execute McpRemoteTool '{self.get_name()}' for remote tool '{remote_tool_name}': {e}",
                exc_info=True
            )
            raise RuntimeError(f"McpRemoteTool execution failed for '{remote_tool_name}': {type(e).__name__} - {str(e)}")
