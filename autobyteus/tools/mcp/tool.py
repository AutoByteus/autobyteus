# file: autobyteus/autobyteus/tools/mcp/tool.py
import logging
from typing import Any, Optional, TYPE_CHECKING

from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema
from .server.proxy import McpServerProxy

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class GenericMcpTool(BaseTool):
    """
    A generic tool wrapper for executing tools on a remote MCP server.
    This tool is a lightweight blueprint. At execution time, it uses a proxy
    to interact with the server, completely hiding the connection management logic.
    """

    def __init__(self,
                 server_id: str,
                 remote_tool_name: str,
                 name: str, 
                 description: str,
                 argument_schema: ParameterSchema):
        """
        Initializes the GenericMcpTool instance with identifiers.
        """
        super().__init__() 
        
        self._server_id = server_id
        self._remote_tool_name = remote_tool_name
        
        # Instance-specific properties for schema generation
        self._instance_name = name
        self._instance_description = description
        self._instance_argument_schema = argument_schema
        
        self.get_name = self.get_instance_name
        self.get_description = self.get_instance_description
        self.get_argument_schema = self.get_instance_argument_schema
        
        logger.info(f"GenericMcpTool instance created for remote tool '{remote_tool_name}' on server '{self._server_id}'. "
                    f"Registered in AutoByteUs as '{self._instance_name}'.")

    # --- Getters for instance-specific data ---
    def get_instance_name(self) -> str: return self._instance_name
    def get_instance_description(self) -> str: return self._instance_description
    def get_instance_argument_schema(self) -> ParameterSchema: return self._instance_argument_schema

    # --- Base class methods (class-level, not instance-level) ---
    @classmethod
    def get_name(cls) -> str: return "GenericMcpTool"
    @classmethod
    def get_description(cls) -> str: return "A generic wrapper for executing remote MCP tools."
    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]: return None 

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> Any:
        """
        Creates a proxy for the remote server and executes the tool call.
        The proxy handles all interaction with the McpServerInstanceManager.
        """
        agent_id = context.agent_id
        tool_name_for_log = self.get_instance_name()
        
        logger.info(f"GenericMcpTool '{tool_name_for_log}': Creating proxy for agent '{agent_id}' and server '{self._server_id}'.")
        
        try:
            # The proxy is created on-demand for each execution.
            proxy = McpServerProxy(agent_id=agent_id, server_id=self._server_id)
            
            return await proxy.call_tool(
                tool_name=self._remote_tool_name,
                arguments=kwargs
            )
        except Exception as e:
            logger.error(
                f"Execution failed for tool '{tool_name_for_log}' on server '{self._server_id}' for agent '{agent_id}': {e}",
                exc_info=True
            )
            raise
