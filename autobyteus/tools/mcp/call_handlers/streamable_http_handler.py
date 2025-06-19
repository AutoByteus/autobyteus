# file: autobyteus/autobyteus/tools/mcp/call_handlers/streamable_http_handler.py
import logging
from typing import Dict, Any, cast, TYPE_CHECKING

from .base_handler import McpCallHandler
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

if TYPE_CHECKING:
    from ..types import BaseMcpConfig, StreamableHttpMcpServerConfig

logger = logging.getLogger(__name__)

class StreamableHttpMcpCallHandler(McpCallHandler):
    """Handles MCP tool calls over a stateless Streamable HTTP transport."""

    async def handle_call(
        self, 
        config: 'BaseMcpConfig', 
        remote_tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Creates a new HTTP connection, establishes a session, and executes the
        requested tool call. It handles 'list_tools' as a special case.
        """
        logger.debug(f"Handling Streamable HTTP call to tool '{remote_tool_name}' on server '{config.server_id}'.")
        
        from ..types import StreamableHttpMcpServerConfig
        if not isinstance(config, StreamableHttpMcpServerConfig):
            raise TypeError(f"StreamableHttpMcpCallHandler requires a StreamableHttpMcpServerConfig, got {type(config).__name__}.")

        http_config = cast(StreamableHttpMcpServerConfig, config)

        try:
            # The streamablehttp_client context manager provides the read/write streams.
            async with streamablehttp_client(http_config.url, headers=http_config.headers) as (read_stream, write_stream):
                # The ClientSession is its own context manager that handles initialization.
                async with ClientSession(read_stream, write_stream) as session:
                    logger.debug(f"Streamable HTTP session established for '{config.server_id}'. Calling tool '{remote_tool_name}'.")

                    # The 'list_tools' command is a special method on the session.
                    if remote_tool_name == "list_tools":
                        result = await session.list_tools()
                    else:
                        result = await session.call_tool(remote_tool_name, arguments)

                    logger.debug(f"Streamable HTTP call to tool '{remote_tool_name}' on server '{config.server_id}' completed.")
                    return result
        except Exception as e:
            logger.error(
                f"An error occurred during Streamable HTTP tool call to '{remote_tool_name}' on server '{config.server_id}': {e}",
                exc_info=True
            )
            raise RuntimeError(f"Failed to execute MCP tool '{remote_tool_name}' via Streamable HTTP on server '{config.server_id}': {e}") from e
