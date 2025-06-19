# file: autobyteus/autobyteus/tools/mcp/call_handlers/base_handler.py
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import BaseMcpConfig

logger = logging.getLogger(__name__)

class McpCallHandler(ABC):
    """
    Abstract base class for a handler that performs a single, end-to-end
    MCP tool call for a specific transport protocol.
    """

    @abstractmethod
    async def handle_call(
        self, 
        config: 'BaseMcpConfig', 
        remote_tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Handles a complete MCP tool call, including connection, execution,
        and disconnection if necessary.

        Args:
            config: The configuration object for the target MCP server.
            remote_tool_name: The name of the tool to call on the remote server.
            arguments: A dictionary of arguments for the tool call.

        Returns:
            The result returned by the remote tool.
            
        Raises:
            NotImplementedError: If the handler for a specific transport is not implemented.
            RuntimeError: If the tool call fails for any reason.
        """
        pass
