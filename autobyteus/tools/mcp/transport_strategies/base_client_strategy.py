# file: autobyteus/autobyteus/tools/mcp/transport_strategies/base_client_strategy.py
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Any, TYPE_CHECKING, Dict, Optional
import asyncio
import uuid

if TYPE_CHECKING:
    # Import from ..types to go up one level from strategies to mcp, then to types
    from ..types import BaseMcpConfig 
    MCPClientHandle = Any # Type alias for objects returned by client factories

logger = logging.getLogger(__name__)

class BaseMcpClientStrategy(ABC):
    """
    Abstract base class for MCP client transport strategies.
    Defines the interface for connecting, disconnecting, and communicating
    with an MCP server.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._pending_requests: Dict[Any, asyncio.Future] = {}
        self._request_lock = asyncio.Lock()

    @abstractmethod
    async def connect(self):
        """Establish a connection to the MCP server."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from the MCP server."""
        pass

    @abstractmethod
    async def send(self, message: dict):
        """Send a message to the MCP server."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the client is connected, False otherwise."""
        pass

    async def _dispatch_message(self, message: dict):
        """
        Callback to be invoked by the strategy's listener when a message is received.
        Resolves the future associated with the message ID.
        """
        async with self._request_lock:
            msg_id = message.get("id")
            if msg_id in self._pending_requests:
                future = self._pending_requests.pop(msg_id)
                if "error" in message:
                    future.set_exception(RuntimeError(f"RPC Error: {message.get('error')}"))
                else:
                    future.set_result(message.get("result"))
            else:
                logger.warning(f"Received message with unmatched id: {msg_id}")

    async def rpc_call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Performs a JSON-RPC call. We now rely on the 'send' method to raise
        an exception if the connection is not active, removing the race condition
        of checking 'is_connected' prematurely.
        """
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id,
        }

        future = asyncio.get_running_loop().create_future()
        async with self._request_lock:
            self._pending_requests[request_id] = future
        
        await self.send(request)

        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            # Clean up the pending request if it times out
            async with self._request_lock:
                self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"RPC call to method '{method}' timed out.")

class McpTransportClientStrategy(ABC):
    """
    Abstract base class for MCP transport client strategies.
    Each strategy knows how to establish a connection for a specific transport type
    and provide the necessary client handle and streams.
    """

    @abstractmethod
    async def create_client_handle(self, config: 'BaseMcpConfig') -> 'MCPClientHandle':
        """
        Creates an asynchronous context manager (client handle) for the connection
        based on the provided configuration.

        Args:
            config: The specific McpServerConfig instance (e.g., StdioMcpServerConfig).

        Returns:
            client_handle: The async context manager that, when entered, will yield
                           the read and write streams for the transport.
        
        Raises:
            NotImplementedError: If the config type is not supported by the strategy.
            RuntimeError: If handle creation fails.
        """
        pass
