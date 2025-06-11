# file: autobyteus/autobyteus/tools/mcp/transport_strategies/streamable_http_client_strategy.py
import logging
from typing import Tuple, Any, TYPE_CHECKING

from .base_client_strategy import McpTransportClientStrategy

# Imports from the external 'mcp' library
from mcp.client.streamable_http import streamablehttp_client as mcp_streamablehttp_client_factory

if TYPE_CHECKING:
    # Import from ..types to go up one level from strategies to mcp, then to types
    from ..types import StreamableHttpMcpServerConfig
    MCPClientHandle = Any

logger = logging.getLogger(__name__)

class StreamableHttpClientStrategy(McpTransportClientStrategy):
    """Strategy for establishing MCP connections via Streamable HTTP."""

    async def create_client_handle(self, config: 'StreamableHttpMcpServerConfig') -> 'MCPClientHandle':
        logger.debug(f"StreamableHttpClientStrategy creating client handle for server_id: '{config.server_id}'")
        if TYPE_CHECKING:
            from ..types import StreamableHttpMcpServerConfig as RuntimeHttpConfig
            if not isinstance(config, RuntimeHttpConfig):
                 raise TypeError(f"StreamableHttpClientStrategy requires StreamableHttpMcpServerConfig, got {type(config).__name__}")
        
        client_handle: 'MCPClientHandle' = mcp_streamablehttp_client_factory(
            config.url,
            headers=config.headers
        )
        
        return client_handle
