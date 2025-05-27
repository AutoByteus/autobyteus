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

    async def establish_connection(self, config: 'StdioMcpServerConfig') -> Tuple['MCPClientHandle', Any, Any]:
        logger.debug(f"StdioClientStrategy establishing connection for server_id: '{config.server_id}'")
        # Type check for config is good practice, though McpConnectionManager should pass the correct type
        if TYPE_CHECKING: # Avoid runtime check if type checking ensures correctness
            from ..types import StdioMcpServerConfig as RuntimeStdioConfig # For isinstance if needed at runtime
            if not isinstance(config, RuntimeStdioConfig):
                raise TypeError(f"StdioClientStrategy requires StdioMcpServerConfig, got {type(config).__name__}")
        
        # Ensure type hint is used if isinstance is not used for runtime check.
        # config: StdioMcpServerConfig # This is already in the signature

        mcp_lib_stdio_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
            cwd=config.cwd
        )
        client_handle: 'MCPClientHandle' = mcp_stdio_client_factory(mcp_lib_stdio_params)
        
        try:
            read_stream, write_stream = await client_handle.__aenter__()
        except Exception as e:
            logger.error(f"StdioClientStrategy: Error during __aenter__ for server '{config.server_id}': {e}", exc_info=True)
            if hasattr(client_handle, '__aexit__'):
                try:
                    await client_handle.__aexit__(type(e), e, e.__traceback__)
                except Exception as exit_e:
                    logger.error(f"StdioClientStrategy: Error during __aexit__ after __aenter__ failure for '{config.server_id}': {exit_e}", exc_info=True)
            raise RuntimeError(f"Failed to enter Stdio client context for server '{config.server_id}': {e}") from e
            
        return client_handle, read_stream, write_stream
