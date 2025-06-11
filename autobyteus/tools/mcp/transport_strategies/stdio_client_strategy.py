# file: autobyteus/autobyteus/tools/mcp/transport_strategies/stdio_client_strategy.py
import logging
from typing import Tuple, Any, TYPE_CHECKING

from .base_client_strategy import McpTransportClientStrategy

# Imports from the external 'mcp' library
from mcp import StdioServerParameters 
from mcp.client.stdio import stdio_client as mcp_stdio_client_factory

if TYPE_CHECKING:
    # Import from ..types to go up one level from strategies to mcp, then to types
    from ..types import StdioMcpServerConfig 
    MCPClientHandle = Any

logger = logging.getLogger(__name__)

class StdioClientStrategy(McpTransportClientStrategy):
    """Strategy for establishing MCP connections via STDIO."""

    async def create_client_handle(self, config: 'StdioMcpServerConfig') -> 'MCPClientHandle':
        logger.debug(f"StdioClientStrategy creating client handle for server_id: '{config.server_id}'")
        if TYPE_CHECKING:
            from ..types import StdioMcpServerConfig as RuntimeStdioConfig
            if not isinstance(config, RuntimeStdioConfig):
                raise TypeError(f"StdioClientStrategy requires StdioMcpServerConfig, got {type(config).__name__}")
        
        mcp_lib_stdio_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
            cwd=config.cwd
        )
        client_handle: 'MCPClientHandle' = mcp_stdio_client_factory(mcp_lib_stdio_params)
        
        return client_handle
