import logging
import asyncio
from typing import cast

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .base_managed_mcp_server import BaseManagedMcpServer
from ..types import StreamableHttpMcpServerConfig

logger = logging.getLogger(__name__)

INITIALIZE_TIMEOUT = 10  # seconds

class HttpManagedMcpServer(BaseManagedMcpServer):
    """Manages the lifecycle of a streamable_http-based MCP server."""

    def __init__(self, config: StreamableHttpMcpServerConfig):
        super().__init__(config)

    async def _create_client_session(self) -> ClientSession:
        """Connects to a remote HTTP endpoint and establishes a client session."""
        config = cast(StreamableHttpMcpServerConfig, self._config)
        
        logger.debug(f"Establishing HTTP connection for server '{self.server_id}' to URL: {config.url}")
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            streamablehttp_client(config.url, headers=config.headers)
        )
        session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

        # --- FIX: Initialize the session after creation with a timeout ---
        try:
            logger.debug(f"Initializing ClientSession for HTTP server '{self.server_id}' with a {INITIALIZE_TIMEOUT}s timeout.")
            await asyncio.wait_for(session.initialize(), timeout=INITIALIZE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(f"Timeout occurred while initializing session for HTTP server '{self.server_id}'. The server did not respond in time.")
            # Re-raise as a standard exception to be handled by the BaseManagedMcpServer's connect method.
            raise ConnectionError(f"Server '{self.server_id}' failed to initialize within the timeout period.")

        logger.debug(f"ClientSession established and initialized for HTTP server '{self.server_id}'.")
        return session
