# file: autobyteus/autobyteus/tools/mcp/server/base_managed_mcp_server.py
import logging
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, types as mcp_types

from ..types import BaseMcpConfig

logger = logging.getLogger(__name__)

class ServerState(str, Enum):
    """Enumerates the possible connection states of a BaseManagedMcpServer."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    CLOSED = "closed"

class BaseManagedMcpServer(ABC):
    """
    Abstract base class representing a connection to a remote MCP server.
    It manages the entire lifecycle and state of a single server connection.
    """
    
    # --- Attributes ---
    _config: BaseMcpConfig
    _state: ServerState
    _connection_lock: asyncio.Lock
    _client_session: Optional[ClientSession]
    _exit_stack: AsyncExitStack

    # --- Initialization ---
    def __init__(self, config: BaseMcpConfig):
        self._config = config
        self._state = ServerState.DISCONNECTED
        self._connection_lock = asyncio.Lock()
        self._client_session = None
        self._exit_stack = AsyncExitStack()

    # --- Public Properties ---
    @property
    def server_id(self) -> str:
        return self._config.server_id

    @property
    def config(self) -> BaseMcpConfig:
        return self._config
        
    @property
    def state(self) -> ServerState:
        return self._state

    # --- Abstract Methods ---
    @abstractmethod
    async def _create_client_session(self) -> ClientSession:
        """
        Transport-specific logic to establish a connection and return a ClientSession.
        This method should leverage self._exit_stack to manage resources.
        """
        pass

    # --- Public API Methods ---
    async def connect(self) -> None:
        """Public method to establish a connection to the server. Idempotent."""
        if self._state == ServerState.CONNECTED:
            return

        async with self._connection_lock:
            # Re-check state after acquiring lock
            if self._state == ServerState.CONNECTED:
                return
            if self._state == ServerState.CONNECTING:
                logger.debug(f"Connection already in progress for '{self.server_id}'. Awaiting completion.")
                # A more advanced implementation might use an asyncio.Event to wait here.
                # For now, serializing via the lock is sufficient.
                return

            logger.info(f"Connecting to MCP server '{self.server_id}'...")
            self._state = ServerState.CONNECTING
            try:
                # The exit stack must be fresh for each connection attempt.
                self._exit_stack = AsyncExitStack()
                self._client_session = await self._create_client_session()
                self._state = ServerState.CONNECTED
                logger.info(f"Successfully connected to MCP server '{self.server_id}'.")
            except Exception as e:
                self._state = ServerState.FAILED
                logger.error(f"Failed to connect to MCP server '{self.server_id}': {e}", exc_info=True)
                # Clean up any partially established resources on failure
                if self._exit_stack:
                    await self._exit_stack.aclose()
                self._client_session = None
                raise

    async def close(self) -> None:
        """Public method to gracefully close the connection to the server."""
        async with self._connection_lock:
            if self._state in [ServerState.DISCONNECTED, ServerState.CLOSED]:
                logger.debug(f"Server '{self.server_id}' is already closed or disconnected. No action taken.")
                return

            logger.info(f"Closing connection to MCP server '{self.server_id}'...")
            self._state = ServerState.CLOSED
            
            try:
                if self._exit_stack:
                    await self._exit_stack.aclose()
            except Exception as e:
                logger.error(f"Error during resource cleanup for server '{self.server_id}': {e}", exc_info=True)
            
            self._client_session = None
            logger.info(f"Connection to MCP server '{self.server_id}' closed.")

    async def list_remote_tools(self) -> List[mcp_types.Tool]:
        """Connects if needed and fetches the list of raw tool objects."""
        if self._state != ServerState.CONNECTED:
            await self.connect()

        if not self._client_session:
            raise RuntimeError(f"Cannot list tools: client session not available for server '{self.server_id}'.")

        logger.debug(f"Listing remote tools on server '{self.server_id}'.")
        result = await self._client_session.list_tools()
        return result.tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Connects if needed and executes a tool call on the remote server."""
        if self._state != ServerState.CONNECTED:
            await self.connect()

        if not self._client_session:
            raise RuntimeError(f"Cannot call tool: client session not available for server '{self.server_id}'.")

        logger.debug(f"Calling remote tool '{tool_name}' on server '{self.server_id}'.")
        return await self._client_session.call_tool(tool_name, arguments)
