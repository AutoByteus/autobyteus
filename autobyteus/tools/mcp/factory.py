# file: autobyteus/autobyteus/mcp/factory.py
import logging
from typing import Optional, TYPE_CHECKING

from .tool import GenericMcpTool
from autobyteus.tools.factory.tool_factory import ToolFactory

if TYPE_CHECKING:
    from autobyteus.utils.parameter_schema import ParameterSchema
    from autobyteus.tools.tool_config import ToolConfig
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class McpToolFactory(ToolFactory):
    """
    A dedicated factory for creating configured instances of GenericMcpTool.
    
    This factory captures the key identifiers of a remote tool (server_id,
    remote_tool_name) and its schema information at the time of discovery.
    """
    def __init__(self,
                 server_id: str,
                 remote_tool_name: str,
                 registered_tool_name: str,
                 tool_description: str,
                 tool_argument_schema: 'ParameterSchema'):
        """
        Initializes the factory with the identifiers and schema of a specific remote tool.
        """
        self._server_id = server_id
        self._remote_tool_name = remote_tool_name
        self._registered_tool_name = registered_tool_name
        self._tool_description = tool_description
        self._tool_argument_schema = tool_argument_schema
        
        logger.debug(
            f"McpToolFactory created for remote tool '{self._remote_tool_name}' "
            f"on server '{self._server_id}' (to be registered as '{self._registered_tool_name}')."
        )

    def create_tool(self, config: Optional['ToolConfig'] = None) -> 'BaseTool':
        """
        Creates and returns a new instance of GenericMcpTool using the
        configuration captured by this factory.
        """
        if config:
            logger.debug(f"McpToolFactory for '{self._registered_tool_name}' received a ToolConfig, which will be ignored.")
            
        return GenericMcpTool(
            server_id=self._server_id,
            remote_tool_name=self._remote_tool_name,
            name=self._registered_tool_name,
            description=self._tool_description,
            argument_schema=self._tool_argument_schema
        )
