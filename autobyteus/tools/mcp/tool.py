# file: autobyteus/autobyteus/mcp/tool.py
import logging
from typing import Any, Optional, TYPE_CHECKING

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from .connection_manager import McpConnectionManager 

logger = logging.getLogger(__name__)

class GenericMcpTool(BaseTool):
    """
    A generic tool wrapper for executing tools on a remote MCP server.
    This tool is instantiated by a custom factory specific to a discovered
    remote MCP tool.
    """

    def __init__(self,
                 mcp_server_id: str, # This now corresponds to McpConfig.server_name
                 mcp_remote_tool_name: str,
                 mcp_connection_manager: 'McpConnectionManager',
                 name: str, 
                 description: str,
                 argument_schema: ParameterSchema):
        """
        Initializes the GenericMcpTool instance.
        These parameters are typically captured and passed by a factory function
        created by the McpToolRegistrar.

        Args:
            mcp_server_id: The unique name/identifier of the MCP server configuration
                           (corresponds to McpConfig.server_name).
            mcp_remote_tool_name: The actual name of the tool on the remote MCP server.
            mcp_connection_manager: Reference to the McpConnectionManager.
            name: The registered name for this tool in AutoByteUs (e.g., prefixed name).
            description: The description for this tool (from remote tool).
            argument_schema: The ParameterSchema for this tool's arguments (mapped from remote tool).
        """
        super().__init__() 
        
        self._mcp_server_id = mcp_server_id # This is McpConfig.server_name
        self._mcp_remote_tool_name = mcp_remote_tool_name
        self._mcp_connection_manager = mcp_connection_manager
        
        self._instance_name = name
        self._instance_description = description
        self._instance_argument_schema = argument_schema
        
        logger.info(f"GenericMcpTool instance created for remote tool '{mcp_remote_tool_name}' on server '{self._mcp_server_id}'. " # Log uses mcp_server_id which is server_name
                    f"Registered in AutoByteUs as '{self._instance_name}'.")

    def get_instance_name(self) -> str:
        return self._instance_name

    def get_instance_description(self) -> str:
        return self._instance_description

    def get_instance_argument_schema(self) -> ParameterSchema:
        return self._instance_argument_schema

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

        Args:
            context: The agent's context.
            **kwargs: Arguments for the remote tool, matching its mapped schema.

        Returns:
            The result from the remote MCP tool.
        
        Raises:
            RuntimeError: If session acquisition or tool call fails.
        """
        logger.info(f"GenericMcpTool '{self._instance_name}': Executing remote tool '{self._mcp_remote_tool_name}' "
                    f"on server '{self._mcp_server_id}' with args: {kwargs}") # Log uses mcp_server_id which is server_name
        
        if not self._mcp_connection_manager: 
             logger.error(f"GenericMcpTool '{self._instance_name}': McpConnectionManager is not set. Cannot execute.")
             raise RuntimeError("McpConnectionManager not available in GenericMcpTool instance.")

        try:
            # self._mcp_server_id is the server_name to use for getting the session
            session = await self._mcp_connection_manager.get_session(self._mcp_server_id)
        except Exception as e:
            logger.error(f"GenericMcpTool '{self._instance_name}': Failed to get MCP session for server '{self._mcp_server_id}': {e}", exc_info=True) # Log uses mcp_server_id
            raise RuntimeError(f"Failed to acquire MCP session for server '{self._mcp_server_id}': {e}") from e

        try:
            result = session.call_tool(self._mcp_remote_tool_name, args=kwargs)
            logger.info(f"GenericMcpTool '{self._instance_name}': Remote tool '{self._mcp_remote_tool_name}' executed successfully. Result preview: {str(result)[:100]}...")
            return result
        except Exception as e:
            logger.error(f"GenericMcpTool '{self._instance_name}': Error calling remote tool '{self._mcp_remote_tool_name}' on server '{self._mcp_server_id}': {e}", exc_info=True) # Log uses mcp_server_id
            raise RuntimeError(f"Error calling remote MCP tool '{self._mcp_remote_tool_name}': {e}") from e
