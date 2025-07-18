# file: autobyteus/autobyteus/tools/mcp/server/http_managed_mcp_server.py
import logging
from typing import cast

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .base_managed_mcp_server import BaseManagedMcpServer
from ..types import StreamableHttpMcpServerConfig

logger = logging.getLogger(__name__)

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
        logger.debug(f"ClientSession established for HTTP server '{self.server_id}'.")
        return session
