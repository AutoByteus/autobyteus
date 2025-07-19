# file: autobyteus/autobyteus/tools/mcp/server/stdio_managed_mcp_server.py
import logging
from typing import cast

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .base_managed_mcp_server import BaseManagedMcpServer
from ..types import StdioMcpServerConfig

logger = logging.getLogger(__name__)

class StdioManagedMcpServer(BaseManagedMcpServer):
    """Manages the lifecycle of a stdio-based MCP server."""

    def __init__(self, config: StdioMcpServerConfig):
        super().__init__(config)

    async def _create_client_session(self) -> ClientSession:
        """Starts a subprocess and establishes a client session over its stdio."""
        config = cast(StdioMcpServerConfig, self._config)
        stdio_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
            cwd=config.cwd
        )
        
        logger.debug(f"Establishing stdio connection for server '{self.server_id}' with command: {config.command}")
        read_stream, write_stream = await self._exit_stack.enter_async_context(stdio_client(stdio_params))
        session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        logger.debug(f"ClientSession established for stdio server '{self.server_id}'.")
        return session
