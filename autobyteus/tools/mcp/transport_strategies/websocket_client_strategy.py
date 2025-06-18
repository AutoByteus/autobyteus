import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

# Handle older versions of the 'websockets' library that do not have the 'enums' module.
try:
    from websockets.enums import State
except ImportError:
    State = None  # type: ignore

from autobyteus.tools.mcp.transport_strategies.base_client_strategy import BaseMcpClientStrategy

logger = logging.getLogger(__name__)

class WebSocketClientStrategy(BaseMcpClientStrategy):
    """MCP client strategy for WebSocket-based communication."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.uri = config.get("uri")
        if not self.uri:
            raise ValueError("WebSocket transport config must include a 'uri'.")
        self._websocket = None
        self._connection_lock = asyncio.Lock()
        self._listener_task: Optional[asyncio.Task] = None

    def _is_websocket_usable(self) -> bool:
        """Internal helper to consistently check if the websocket object is connected."""
        if self._websocket is None:
            return False
        # The 'open' attribute is the most reliable indicator of a usable connection.
        if hasattr(self._websocket, 'open'):
            return self._websocket.open
        # Fallback for older versions that may not have 'open' but have 'closed'.
        if hasattr(self._websocket, 'closed'):
            return not self._websocket.closed
        return False

    async def connect(self):
        """Establishes a WebSocket connection."""
        async with self._connection_lock:
            if self._is_websocket_usable():
                logger.info("WebSocket connection already established.")
                return

            try:
                # The 'websockets' library is required for this strategy.
                import websockets
            except ImportError:
                logger.error("The 'websockets' library is required for WebSocket transport. Please run 'pip install websockets'.")
                raise

            try:
                logger.info(f"Connecting to WebSocket server at {self.uri}...")
                self._websocket = await websockets.connect(self.uri)
                # Start a background task to listen for incoming messages
                self._listener_task = asyncio.create_task(self._listen_for_messages())
                logger.info(f"Successfully connected to WebSocket server at {self.uri}.")
            except Exception as e:
                logger.error(f"Failed to connect to WebSocket server at {self.uri}: {e}")
                self._websocket = None
                raise

    async def disconnect(self):
        """Closes the WebSocket connection."""
        async with self._connection_lock:
            if self._websocket:
                logger.info(f"Closing WebSocket connection to {self.uri}...")
                await self._websocket.close()
                self._websocket = None
                logger.info("WebSocket connection closed.")
            if self._listener_task and not self._listener_task.done():
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass # Expected on cancellation
            self._listener_task = None


    async def send(self, message: dict):
        """Sends a message to the WebSocket server."""
        if not self.is_connected:
            logger.warning("WebSocket is not connected. Attempting to reconnect...")
            await self.connect()
        
        if self._websocket:
            try:
                await self._websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message via WebSocket: {e}")
                # Consider a retry mechanism or connection check here
                raise

    async def _listen_for_messages(self):
        """A background task that continuously listens for incoming messages."""
        if not self._websocket:
            return
        try:
            async for message_str in self._websocket:
                try:
                    message = json.loads(message_str)
                    await self._dispatch_message(message)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode incoming WebSocket message: {message_str}")
        except Exception as e:
            # This can happen if the connection is closed abruptly.
            logger.info(f"Listener task for {self.uri} stopped. Reason: {e}")
        finally:
            logger.debug(f"WebSocket listener task for {self.uri} has finished.")

    @property
    def is_connected(self) -> bool:
        """Returns True if the WebSocket is connected and usable."""
        return self._is_websocket_usable()