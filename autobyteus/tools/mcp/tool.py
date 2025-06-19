# file: autobyteus/autobyteus/tools/mcp/tool.py
import logging
from typing import Any, Optional, TYPE_CHECKING

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from .call_handlers.base_handler import McpCallHandler
    from .types import BaseMcpConfig

logger = logging.getLogger(__name__)

class GenericMcpTool(BaseTool):
    """
    A generic tool wrapper for executing tools on a remote MCP server.
    This tool delegates the entire remote call, including connection and
    protocol specifics, to an MCP call handler.
    """

    def __init__(self,
                 mcp_server_config: 'BaseMcpConfig',
                 mcp_remote_tool_name: str,
                 mcp_call_handler: 'McpCallHandler',
                 name: str, 
                 description: str,
                 argument_schema: ParameterSchema):
        """
        Initializes the GenericMcpTool instance.
        """
        super().__init__() 
        
        self._mcp_server_config = mcp_server_config
        self._mcp_remote_tool_name = mcp_remote_tool_name
        self._mcp_call_handler = mcp_call_handler
        
        self._instance_name = name
        self._instance_description = description
        self._instance_argument_schema = argument_schema
        
        # Override the base class's schema-related methods with instance-specific
        # versions for correct validation and usage generation.
        self.get_name = self.get_instance_name
        self.get_description = self.get_instance_description
        self.get_argument_schema = self.get_instance_argument_schema
        
        logger.info(f"GenericMcpTool instance created for remote tool '{mcp_remote_tool_name}' on server '{self._mcp_server_config.server_id}'. "
                    f"Registered in AutoByteUs as '{self._instance_name}'.")

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
        Executes the remote MCP tool by delegating to the injected call handler.
        """
        tool_name_for_log = self.get_instance_name()
        logger.info(f"GenericMcpTool '{tool_name_for_log}': Delegating call for remote tool '{self._mcp_remote_tool_name}' "
                    f"on server '{self._mcp_server_config.server_id}' to handler.")
        
        if not self._mcp_call_handler:
             logger.error(f"GenericMcpTool '{tool_name_for_log}': McpCallHandler is not set. Cannot execute.")
             raise RuntimeError("McpCallHandler not available in GenericMcpTool instance.")

        try:
            # The handler is responsible for the entire end-to-end call.
            return await self._mcp_call_handler.handle_call(
                config=self._mcp_server_config,
                remote_tool_name=self._mcp_remote_tool_name,
                arguments=kwargs
            )
        except Exception as e:
            logger.error(
                f"The MCP call handler for tool '{tool_name_for_log}' raised an exception: {e}",
                exc_info=True
            )
            # Re-raise to ensure the agent knows the tool call failed.
            raise
