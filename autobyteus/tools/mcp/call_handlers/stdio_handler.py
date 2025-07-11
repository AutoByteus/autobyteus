# file: autobyteus/autobyteus/tools/mcp/call_handlers/stdio_handler.py
import logging
import asyncio
from typing import Dict, Any, cast, TYPE_CHECKING

from .base_handler import McpCallHandler
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

if TYPE_CHECKING:
    from ..types import BaseMcpConfig, StdioMcpServerConfig

logger = logging.getLogger(__name__)

# A default timeout for STDIO subprocesses to prevent indefinite hangs.
DEFAULT_STDIO_TIMEOUT = 30  # seconds

class StdioMcpCallHandler(McpCallHandler):
    """Handles MCP tool calls over a stateless STDIO transport."""

    async def handle_call(
        self, 
        config: 'BaseMcpConfig', 
        remote_tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Creates a new subprocess, establishes a session, and executes the
        requested tool call. It handles 'list_tools' as a special case.
        Includes a timeout to prevent hanging on unresponsive subprocesses.
        """
        logger.debug(f"Handling STDIO call to tool '{remote_tool_name}' on server '{config.server_id}'.")
        
        from ..types import StdioMcpServerConfig
        if not isinstance(config, StdioMcpServerConfig):
            raise TypeError(f"StdioMcpCallHandler requires a StdioMcpServerConfig, but got {type(config).__name__}.")
        
        stdio_config = cast(StdioMcpServerConfig, config)

        mcp_lib_stdio_params = StdioServerParameters(
            command=stdio_config.command,
            args=stdio_config.args,
            env=stdio_config.env,
            cwd=stdio_config.cwd
        )

        async def _perform_call():
            """Inner function to be wrapped by the timeout."""
            # The stdio_client context manager provides the read/write streams.
            async with stdio_client(mcp_lib_stdio_params) as (read_stream, write_stream):
                # The ClientSession is its own context manager that handles initialization.
                async with ClientSession(read_stream, write_stream) as session:
                    logger.debug(f"STDIO session established for '{config.server_id}'. Calling tool '{remote_tool_name}'.")
                    
                    # The 'list_tools' command is a special method on the session.
                    if remote_tool_name == "list_tools":
                        result = await session.list_tools()
                    else:
                        result = await session.call_tool(remote_tool_name, arguments)
                    
                    logger.debug(f"STDIO call to tool '{remote_tool_name}' on server '{config.server_id}' completed.")
                    return result

        try:
            return await asyncio.wait_for(_perform_call(), timeout=DEFAULT_STDIO_TIMEOUT)
        except asyncio.TimeoutError:
            error_message = (f"MCP call to '{remote_tool_name}' on server '{config.server_id}' timed out "
                             f"after {DEFAULT_STDIO_TIMEOUT} seconds. The subprocess may have hung.")
            logger.error(error_message)
            raise RuntimeError(error_message) from None
        except Exception as e:
            logger.error(
                f"An error occurred during STDIO tool call to '{remote_tool_name}' on server '{config.server_id}': {e}",
                exc_info=True
            )
            raise RuntimeError(f"Failed to execute MCP tool '{remote_tool_name}' via STDIO on server '{config.server_id}': {e}") from e
