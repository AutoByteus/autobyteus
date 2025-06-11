# file: autobyteus/autobyteus/tools/mcp/connection_manager.py
import logging
import asyncio
from contextlib import AsyncExitStack
from typing import Dict, Optional, Any, Tuple

from autobyteus.utils.singleton import SingletonMeta
from .types import BaseMcpConfig, McpTransportType
from .config_service import McpConfigService
from .transport_strategies import (
    McpTransportClientStrategy,
    StdioClientStrategy,
    StreamableHttpClientStrategy,
    SseClientStrategy
)

from mcp import ClientSession

logger = logging.getLogger(__name__)

class McpConnectionManager(metaclass=SingletonMeta):
    """
    Manages transport-specific connections to MCP servers using transport strategies
    and provides mcp.ClientSession objects. Uses AsyncExitStack for robust
    resource management of connections.
    """
    def __init__(self, config_service: McpConfigService):
        if not isinstance(config_service, McpConfigService):
            raise TypeError("McpConnectionManager requires an McpConfigService instance.")
        self._config_service: McpConfigService = config_service
        self._managed_connections: Dict[str, Tuple[ClientSession, AsyncExitStack]] = {}
        self._lock = asyncio.Lock()
        
        self._transport_strategies: Dict[McpTransportType, McpTransportClientStrategy] = {
            McpTransportType.STDIO: StdioClientStrategy(),
            McpTransportType.STREAMABLE_HTTP: StreamableHttpClientStrategy(),
            McpTransportType.SSE: SseClientStrategy(),
        }
        logger.info(f"McpConnectionManager initialized with {len(self._transport_strategies)} transport strategies.")

    async def get_session(self, server_id: str) -> ClientSession:
        """
        Retrieves or creates an mcp.ClientSession for the given server_id.
        The session will be initialized and its resources managed by an AsyncExitStack.
        """
        async with self._lock:
            if server_id in self._managed_connections:
                session, _ = self._managed_connections[server_id]
                logger.debug(f"Returning existing MCP session for server_id: '{server_id}'.")
                return session

            mcp_config: Optional[BaseMcpConfig] = self._config_service.get_config(server_id)
            if not mcp_config:
                raise ValueError(f"MCP configuration not found for server_id: {server_id}")
            if not mcp_config.enabled:
                raise ValueError(f"MCP server_id: '{server_id}' is disabled.")

            logger.info(f"Creating new MCP connection and session for server_id: '{server_id}' using transport: {mcp_config.transport_type.value}.")
            
            exit_stack = AsyncExitStack()
            session: Optional[ClientSession] = None
            
            try:
                strategy = self._transport_strategies.get(mcp_config.transport_type)
                if not strategy:
                    raise ValueError(f"No transport strategy found for transport type '{mcp_config.transport_type.value}' of server '{server_id}'.")

                # 1. Create the transport handle (a context manager)
                transport_handle = await strategy.create_client_handle(mcp_config)

                # 2. Let the exit_stack manage the transport handle's lifecycle.
                # This calls transport_handle.__aenter__() and schedules __aexit__ for cleanup.
                # For stdio, this starts the subprocess.
                transport_result = await exit_stack.enter_async_context(transport_handle)
                
                # The result from the transport context depends on the transport type.
                # For stdio and streamable_http, it's typically (read_stream, write_stream, ...).
                if isinstance(transport_result, tuple) and len(transport_result) >= 2:
                    read_stream, write_stream = transport_result[0], transport_result[1]
                else:
                    raise RuntimeError(f"Transport for '{server_id}' did not return expected streams.")

                # 3. Create the ClientSession.
                session = ClientSession(read_stream, write_stream)

                # 4. Let the exit_stack also manage the session's lifecycle.
                # This calls session.__aenter__(), which is session.initialize().
                # It also schedules session.__aexit__(), which is session.close().
                await exit_stack.enter_async_context(session)

                # 5. Store the session and its managing exit_stack.
                self._managed_connections[server_id] = (session, exit_stack)
                logger.info(f"MCP session successfully created, initialized, and stored for server_id: '{server_id}'.")
                return session

            except Exception as e:
                logger.error(f"Failed to create MCP session for server_id '{server_id}': {e}", exc_info=True)
                # If any step failed, the exit_stack will clean up any resources
                # that were successfully entered before the failure.
                await exit_stack.aclose()
                raise RuntimeError(f"Failed to create MCP session for server_id '{server_id}': {e}") from e

    async def close_session(self, server_id: str) -> None:
        async with self._lock:
            if server_id in self._managed_connections:
                _, exit_stack = self._managed_connections.pop(server_id)
                logger.info(f"Closing MCP connection for server_id: '{server_id}'...")
                await exit_stack.aclose()
                logger.info(f"MCP connection for server_id: '{server_id}' closed.")
            else:
                logger.debug(f"No active session found to close for server_id: '{server_id}'.")

    async def close_all_sessions(self) -> None:
        logger.info("Closing all active MCP sessions and their resources.")
        async with self._lock:
            server_ids_to_close = list(self._managed_connections.keys())
            for server_id in server_ids_to_close:
                # Use a separate try/except for each connection to ensure all are attempted
                try:
                    await self.close_session(server_id)
                except Exception as e:
                    logger.error(f"Error while closing connection for server_id '{server_id}': {e}", exc_info=True)
        
        self._managed_connections.clear()
        logger.info("All MCP sessions have been requested to close.")

    async def cleanup(self):
        await self.close_all_sessions()
