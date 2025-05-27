# file: autobyteus/autobyteus/tools/mcp/connection_manager.py
import logging
import asyncio
from typing import Dict, Optional, Any, Tuple, Union, Type

from autobyteus.utils.singleton import SingletonMeta
from .types import (
    BaseMcpConfig, 
    # StdioMcpServerConfig, # Not directly used here anymore, but by strategies
    # SseMcpServerConfig, 
    # StreamableHttpMcpServerConfig, 
    McpTransportType
)
from .config_service import McpConfigService
# UPDATED IMPORT: Import from the new sub-package
from .transport_strategies import ( 
    McpTransportClientStrategy, # Still useful for type hinting _transport_strategies dict value
    StdioClientStrategy,
    StreamableHttpClientStrategy,
    SseClientStrategy
)

from mcp import ClientSession

logger = logging.getLogger(__name__)

MCPClientHandle = Any 

class McpConnectionManager(metaclass=SingletonMeta):
    """
    Manages transport-specific connections to MCP servers using transport strategies
    and provides mcp.ClientSession objects.
    """
    def __init__(self, config_service: McpConfigService):
        if not isinstance(config_service, McpConfigService):
            raise TypeError("McpConnectionManager requires an McpConfigService instance.")
        self._config_service: McpConfigService = config_service
        self._active_sessions: Dict[str, ClientSession] = {} 
        self._managed_client_handles: Dict[str, MCPClientHandle] = {} 
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
        The session will be initialized.
        """
        async with self._lock:
            if server_id in self._active_sessions:
                session_to_return = self._active_sessions[server_id]
                logger.debug(f"Returning existing MCP session for server_id: '{server_id}'.")
                return session_to_return

            mcp_config: Optional[BaseMcpConfig] = self._config_service.get_config(server_id)
            if not mcp_config:
                raise ValueError(f"MCP configuration not found for server_id: {server_id}")
            if not mcp_config.enabled:
                raise ValueError(f"MCP server_id: '{server_id}' is disabled.")

            logger.info(f"Creating new MCP connection and session for server_id: '{server_id}' using transport: {mcp_config.transport_type.value}.")
            
            client_handle: Optional[MCPClientHandle] = None
            session: Optional[ClientSession] = None
            # read_stream and write_stream are now populated by the strategy call

            strategy = self._transport_strategies.get(mcp_config.transport_type)
            if not strategy:
                raise ValueError(f"No transport strategy found for transport type '{mcp_config.transport_type.value}' of server '{server_id}'.")

            try:
                # The specific config type (e.g. StdioMcpServerConfig) is passed to the strategy.
                # The strategy's type hint for its 'config' param should match.
                client_handle, read_stream, write_stream = await strategy.establish_connection(mcp_config)
                
                if not client_handle or read_stream is None or write_stream is None:
                    if client_handle and hasattr(client_handle, '__aexit__'):
                         await client_handle.__aexit__(None, None, None) 
                    raise RuntimeError(f"Transport strategy for '{mcp_config.transport_type.value}' failed to provide valid streams/handle for MCP server '{server_id}'.")

                session = ClientSession(read_stream, write_stream)
                await session.initialize()

                self._managed_client_handles[server_id] = client_handle 
                self._active_sessions[server_id] = session
                logger.info(f"MCP session successfully created, initialized, and stored for server_id: '{server_id}'.")
                return session

            except Exception as e: 
                logger.error(f"Failed to create MCP session for server_id '{server_id}': {e}", exc_info=True)
                if client_handle and self._managed_client_handles.get(server_id) != client_handle: 
                    if hasattr(client_handle, '__aexit__'): 
                        try:
                            await client_handle.__aexit__(type(e), e, e.__traceback__)
                        except Exception as exit_err:
                            logger.error(f"Error exiting client handle context for '{server_id}' after failure: {exit_err}", exc_info=True)
                raise RuntimeError(f"Failed to create MCP session for server_id '{server_id}': {e}") from e


    async def close_session(self, server_id: str) -> None: 
        async with self._lock:
            session = self._active_sessions.pop(server_id, None)
            client_handle = self._managed_client_handles.pop(server_id, None) 
            closed_something = False

            if session and hasattr(session, 'close') and asyncio.iscoroutinefunction(session.close):
                try:
                    await session.close()
                    logger.info(f"MCP ClientSession closed for server_id: '{server_id}'.")
                    closed_something = True
                except Exception as e:
                    logger.error(f"Error closing MCP ClientSession for '{server_id}': {e}", exc_info=True)
            
            if client_handle and hasattr(client_handle, '__aexit__'):
                try:
                    await client_handle.__aexit__(None, None, None) 
                    logger.info(f"MCP client handle context exited for server_id: '{server_id}'.")
                    closed_something = True
                except Exception as e:
                    logger.error(f"Error exiting MCP client handle context for '{server_id}': {e}", exc_info=True)
            
            if not closed_something:
                logger.debug(f"No active session or client handle found to close for server_id: '{server_id}'.")

    async def close_all_sessions(self) -> None:
        logger.info("Closing all active MCP sessions and client handles.")
        async with self._lock:
            server_ids_list = list(self._active_sessions.keys()) 
            for server_id_item in server_ids_list: 
                session = self._active_sessions.pop(server_id_item, None)
                client_handle = self._managed_client_handles.pop(server_id_item, None)
                
                if session and hasattr(session, 'close') and asyncio.iscoroutinefunction(session.close):
                    try: await session.close()
                    except Exception as e: logger.error(f"Error closing ClientSession for '{server_id_item}': {e}", exc_info=True)
                
                if client_handle and hasattr(client_handle, '__aexit__'):
                    try: await client_handle.__aexit__(None, None, None)
                    except Exception as e: logger.error(f"Error exiting client handle context for '{server_id_item}': {e}", exc_info=True)
            
            self._active_sessions.clear()
            self._managed_client_handles.clear()
        logger.info("All MCP sessions and client handles have been requested to close.")

    async def cleanup(self):
        await self.close_all_sessions()
