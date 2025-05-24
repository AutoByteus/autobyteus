# file: autobyteus/autobyteus/mcp/connection_manager.py
import logging
import asyncio
from typing import Dict, Optional, Any, Tuple, Union

from autobyteus.utils.singleton import SingletonMeta
# Corrected imports to use relative paths for sibling modules within the mcp package
from .types import McpConfig, McpTransportType
from .config_service import McpConfigService


# Imports from the (hypothetical or actual) external 'mcp' library
# Based on user-provided examples
# If these imports fail, an ImportError will be raised, which is standard.
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client as mcp_stdio_client_factory
from mcp.client.streamable_http import streamablehttp_client as mcp_streamablehttp_client_factory
from mcp.client.auth import OAuthClientProvider # For type hinting if ever used

logger = logging.getLogger(__name__)

MCPClientHandle = Any # Type alias for objects returned by client factories

class McpConnectionManager(metaclass=SingletonMeta):
    """
    Manages transport-specific connections (stdio, streamable_http) to MCP servers
    and provides mcp.ClientSession objects. Abstracts transport details.
    This is a singleton.
    """
    def __init__(self, config_service: McpConfigService):
        if not isinstance(config_service, McpConfigService):
            raise TypeError("McpConnectionManager requires an McpConfigService instance.")
        self._config_service: McpConfigService = config_service
        self._active_sessions: Dict[str, ClientSession] = {} # Key is server_name
        self._managed_client_handles: Dict[str, MCPClientHandle] = {} # Key is server_name
        self._lock = asyncio.Lock() 
        logger.info("McpConnectionManager initialized.")

    async def get_session(self, server_name: str) -> ClientSession: # Renamed server_id to server_name
        """
        Retrieves or creates an mcp.ClientSession for the given server_name.
        The session will be initialized.
        """
        async with self._lock:
            if server_name in self._active_sessions:
                session_to_return = self._active_sessions[server_name]
                # TODO: Implement session health check if library supports
                logger.debug(f"Returning existing MCP session for server_name: '{server_name}'.") # UPDATED
                return session_to_return

            mcp_config: Optional[McpConfig] = self._config_service.get_config(server_name) # UPDATED param name for clarity
            if not mcp_config:
                raise ValueError(f"MCP configuration not found for server_name: {server_name}") # UPDATED
            if not mcp_config.enabled:
                raise ValueError(f"MCP server_name: '{server_name}' is disabled.") # UPDATED

            logger.info(f"Creating new MCP connection and session for server_name: '{server_name}' using transport: {mcp_config.transport_type.value}.") # UPDATED
            
            client_handle: Optional[MCPClientHandle] = None
            session: Optional[ClientSession] = None
            read_stream: Any = None
            write_stream: Any = None

            try:
                if mcp_config.transport_type == McpTransportType.STDIO:
                    if not mcp_config.stdio_params:
                        raise ValueError(f"Stdio parameters missing for server '{server_name}'.") # UPDATED
                    mcp_lib_stdio_params = StdioServerParameters(
                        command=mcp_config.stdio_params.command,
                        args=mcp_config.stdio_params.args,
                        env=mcp_config.stdio_params.env,
                        cwd=mcp_config.stdio_params.cwd
                    )
                    client_handle = mcp_stdio_client_factory(mcp_lib_stdio_params)
                    streams_tuple = await client_handle.__aenter__()
                    if len(streams_tuple) == 2: # stdio returns (read, write)
                        read_stream, write_stream = streams_tuple
                    else:
                        if hasattr(client_handle, '__aexit__'): await client_handle.__aexit__(None,None,None)
                        raise RuntimeError(f"Stdio client for '{server_name}' returned unexpected stream tuple format.") # UPDATED

                elif mcp_config.transport_type == McpTransportType.STREAMABLE_HTTP:
                    if not mcp_config.streamable_http_params:
                        raise ValueError(f"Streamable HTTP parameters missing for server '{server_name}'.") # UPDATED
                    
                    client_handle = mcp_streamablehttp_client_factory(
                        mcp_config.streamable_http_params.url, 
                        headers=mcp_config.streamable_http_params.headers
                    )
                    streams_tuple_http = await client_handle.__aenter__()
                    read_stream, write_stream, _ = streams_tuple_http 
                else:
                    raise ValueError(f"Unsupported or not yet implemented MCP transport type: {mcp_config.transport_type} for server '{server_name}'.") # UPDATED

                if not client_handle or read_stream is None or write_stream is None:
                    if client_handle and hasattr(client_handle, '__aexit__'): await client_handle.__aexit__(None,None,None)
                    raise RuntimeError(f"Failed to establish streams for MCP server '{server_name}'.") # UPDATED

                session = ClientSession(read_stream, write_stream)
                await session.initialize()

                self._managed_client_handles[server_name] = client_handle # UPDATED
                self._active_sessions[server_name] = session # UPDATED
                logger.info(f"MCP session successfully created, initialized, and stored for server_name: '{server_name}'.") # UPDATED
                return session

            except Exception as e: 
                logger.error(f"Failed to create MCP session for server_name '{server_name}': {e}", exc_info=True) # UPDATED
                if client_handle and hasattr(client_handle, '__aexit__'): 
                    try:
                        await client_handle.__aexit__(None, None, None)
                    except Exception as exit_err:
                        logger.error(f"Error exiting client handle context for '{server_name}' after failure: {exit_err}", exc_info=True) # UPDATED
                raise RuntimeError(f"Failed to create MCP session for server_name '{server_name}': {e}") from e # UPDATED


    async def close_session(self, server_name: str) -> None: # Renamed server_id to server_name
        async with self._lock:
            session = self._active_sessions.pop(server_name, None) # UPDATED
            client_handle = self._managed_client_handles.pop(server_name, None) # UPDATED
            closed_something = False

            if session and hasattr(session, 'close') and asyncio.iscoroutinefunction(session.close):
                try:
                    await session.close()
                    logger.info(f"MCP ClientSession closed for server_name: '{server_name}'.") # UPDATED
                    closed_something = True
                except Exception as e:
                    logger.error(f"Error closing MCP ClientSession for '{server_name}': {e}", exc_info=True) # UPDATED
            
            if client_handle and hasattr(client_handle, '__aexit__'):
                try:
                    await client_handle.__aexit__(None, None, None)
                    logger.info(f"MCP client handle context exited for server_name: '{server_name}'.") # UPDATED
                    closed_something = True
                except Exception as e:
                    logger.error(f"Error exiting MCP client handle context for '{server_name}': {e}", exc_info=True) # UPDATED
            
            if not closed_something:
                logger.debug(f"No active session or client handle found to close for server_name: '{server_name}'.") # UPDATED

    async def close_all_sessions(self) -> None:
        logger.info("Closing all active MCP sessions and client handles.")
        async with self._lock:
            server_names_list = list(self._active_sessions.keys()) # UPDATED: server_ids to server_names_list
            for server_name_item in server_names_list: # UPDATED
                session = self._active_sessions.pop(server_name_item, None)
                client_handle = self._managed_client_handles.pop(server_name_item, None)
                
                if session and hasattr(session, 'close') and asyncio.iscoroutinefunction(session.close):
                    try: await session.close()
                    except Exception as e: logger.error(f"Error closing ClientSession for '{server_name_item}': {e}", exc_info=True) # UPDATED
                
                if client_handle and hasattr(client_handle, '__aexit__'):
                    try: await client_handle.__aexit__(None, None, None)
                    except Exception as e: logger.error(f"Error exiting client handle context for '{server_name_item}': {e}", exc_info=True) # UPDATED
            
            self._active_sessions.clear()
            self._managed_client_handles.clear()
        logger.info("All MCP sessions and client handles have been requested to close.")

    async def cleanup(self):
        await self.close_all_sessions()
