# file: autobyteus/autobyteus/tools/mcp/transport_strategies/base_client_strategy.py
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    # Import from ..types to go up one level from strategies to mcp, then to types
    from ..types import BaseMcpConfig 
    MCPClientHandle = Any # Type alias for objects returned by client factories

logger = logging.getLogger(__name__)

class McpTransportClientStrategy(ABC):
    """
    Abstract base class for MCP transport client strategies.
    Each strategy knows how to establish a connection for a specific transport type
    and provide the necessary client handle and streams.
    """

    @abstractmethod
    async def establish_connection(self, config: 'BaseMcpConfig') -> Tuple['MCPClientHandle', Any, Any]:
        """
        Establishes a connection based on the provided configuration.

        Args:
            config: The specific McpServerConfig instance (e.g., StdioMcpServerConfig).

        Returns:
            A tuple containing:
            - client_handle: The handle returned by the mcp client factory (needs __aenter__/__aexit__).
            - read_stream: The stream for reading data from the MCP server.
            - write_stream: The stream for writing data to the MCP server.
        
        Raises:
            NotImplementedError: If the config type is not supported by the strategy.
            RuntimeError: If connection establishment fails.
        """
        pass
