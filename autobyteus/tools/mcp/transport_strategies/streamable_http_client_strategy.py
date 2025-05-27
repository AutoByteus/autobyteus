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

    async def establish_connection(self, config: 'StreamableHttpMcpServerConfig') -> Tuple['MCPClientHandle', Any, Any]:
        logger.debug(f"StreamableHttpClientStrategy establishing connection for server_id: '{config.server_id}'")
        if TYPE_CHECKING: # Avoid runtime check if type checking ensures correctness
            from ..types import StreamableHttpMcpServerConfig as RuntimeHttpConfig
            if not isinstance(config, RuntimeHttpConfig):
                 raise TypeError(f"StreamableHttpClientStrategy requires StreamableHttpMcpServerConfig, got {type(config).__name__}")
        
        # config: StreamableHttpMcpServerConfig # Already in signature

        client_handle: 'MCPClientHandle' = mcp_streamablehttp_client_factory(
            config.url,
            headers=config.headers
        )
        
        try:
            # Assuming the factory's __aenter__ returns (read_stream, write_stream, response_obj_or_none)
            read_stream, write_stream, _ = await client_handle.__aenter__() 
        except Exception as e:
            logger.error(f"StreamableHttpClientStrategy: Error during __aenter__ for server '{config.server_id}': {e}", exc_info=True)
            if hasattr(client_handle, '__aexit__'):
                try:
                    await client_handle.__aexit__(type(e), e, e.__traceback__)
                except Exception as exit_e:
                    logger.error(f"StreamableHttpClientStrategy: Error during __aexit__ after __aenter__ failure for '{config.server_id}': {exit_e}", exc_info=True)
            raise RuntimeError(f"Failed to enter StreamableHttp client context for server '{config.server_id}': {e}") from e

        return client_handle, read_stream, write_stream
