# file: autobyteus/autobyteus/mcp/factory.py
import logging
from typing import Optional, TYPE_CHECKING

from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.tools.factory.tool_factory import ToolFactory

if TYPE_CHECKING:
    from autobyteus.tools.mcp.call_handlers.base_handler import McpCallHandler
    from autobyteus.tools.mcp.types import BaseMcpConfig
    from autobyteus.tools.parameter_schema import ParameterSchema
    from autobyteus.tools.tool_config import ToolConfig
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class McpToolFactory(ToolFactory):
    """
    A dedicated factory for creating configured instances of GenericMcpTool.
    
    This factory captures the necessary context at the time of tool discovery
    (e.g., server config, remote tool name, call handler) and uses it to 
    instantiate a GenericMcpTool when requested by the ToolRegistry.
    """
    def __init__(self,
                 mcp_server_config: 'BaseMcpConfig',
                 mcp_remote_tool_name: str,
                 mcp_call_handler: 'McpCallHandler',
                 registered_tool_name: str,
                 tool_description: str,
                 tool_argument_schema: 'ParameterSchema'):
        """
        Initializes the factory with the context of a specific remote tool.
        """
        self._mcp_server_config = mcp_server_config
        self._mcp_remote_tool_name = mcp_remote_tool_name
        self._mcp_call_handler = mcp_call_handler
        self._registered_tool_name = registered_tool_name
        self._tool_description = tool_description
        self._tool_argument_schema = tool_argument_schema
        
        logger.debug(
            f"McpToolFactory created for remote tool '{self._mcp_remote_tool_name}' "
            f"on server '{self._mcp_server_config.server_id}' (to be registered as '{self._registered_tool_name}')."
        )

    def create_tool(self, config: Optional['ToolConfig'] = None) -> 'BaseTool':
        """
        Creates and returns a new instance of GenericMcpTool using the
        configuration captured by this factory.

        Args:
            config: An optional ToolConfig. This is part of the standard factory
                    interface but is not used by this specific factory, as all
                    configuration is provided during initialization.
        
        Returns:
            A configured instance of GenericMcpTool.
        """
        if config:
            logger.debug(f"McpToolFactory for '{self._registered_tool_name}' received a ToolConfig, which will be ignored.")
            
        return GenericMcpTool(
            mcp_server_config=self._mcp_server_config,
            mcp_remote_tool_name=self._mcp_remote_tool_name,
            mcp_call_handler=self._mcp_call_handler,
            name=self._registered_tool_name,
            description=self._tool_description,
            argument_schema=self._tool_argument_schema
        )
