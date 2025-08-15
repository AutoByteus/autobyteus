import logging
import asyncio
from typing import cast

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .base_managed_mcp_server import BaseManagedMcpServer
from ..types import StdioMcpServerConfig

logger = logging.getLogger(__name__)

INITIALIZE_TIMEOUT = 10  # seconds

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
        
        # --- FIX: Initialize the session after creation with a timeout ---
        try:
            logger.debug(f"Initializing ClientSession for stdio server '{self.server_id}' with a {INITIALIZE_TIMEOUT}s timeout.")
            await asyncio.wait_for(session.initialize(), timeout=INITIALIZE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(f"Timeout occurred while initializing session for server '{self.server_id}'. The server did not respond in time.")
            # Re-raise as a standard exception to be handled by the BaseManagedMcpServer's connect method.
            raise ConnectionError(f"Server '{self.server_id}' failed to initialize within the timeout period.")
        
        logger.debug(f"ClientSession established and initialized for stdio server '{self.server_id}'.")
        return session
