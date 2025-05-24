# file: autobyteus/autobyteus/rpc/client/abstract_client_connection.py
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any # Added Dict, Any

from autobyteus.rpc.protocol import ProtocolMessage

logger = logging.getLogger(__name__)

class AbstractClientConnection(ABC):
    """
    Abstract base class for client-side connections to an Agent Server.
    Defines the common interface for sending requests and handling responses/events.
    """

    def __init__(self, server_id: str):
        self.server_id = server_id
        self._is_connected: bool = False
        self._connection_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """Indicates if the connection is currently active."""
        return self._is_connected

    @abstractmethod
    async def connect(self) -> None:
        """
        Establishes the connection to the remote server.
        Sets _is_connected to True on success.
        Raises:
            ConnectionError: If connection fails.
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """
        Closes the connection to the remote server.
        Sets _is_connected to False.
        """
        raise NotImplementedError

    @abstractmethod
    async def send_request(self, request_message: ProtocolMessage) -> ProtocolMessage:
        """
        Sends a request ProtocolMessage to the server and awaits a corresponding
        response ProtocolMessage (either a result or an error).

        Args:
            request_message: The ProtocolMessage to send (must be of type REQUEST).

        Returns:
            The response ProtocolMessage from the server.

        Raises:
            ConnectionError: If not connected or if communication fails.
            TimeoutError: If the server does not respond within a reasonable time.
            ValueError: If request_message is not a valid request.
        """
        raise NotImplementedError

    async def events(self) -> AsyncIterator[ProtocolMessage]: # pragma: no cover
        """
        (Optional for some connection types like stdio, primary for SSE)
        Provides an asynchronous iterator for server-pushed events.

        Yields:
            ProtocolMessage objects of type EVENT from the server.

        Raises:
            ConnectionError: If not connected or if the event stream fails.
        """
        # Default implementation for connection types that don't support server-pushed events.
        if False: # This makes the method an async generator while doing nothing
            yield
        logger.warning(f"Connection type {self.__class__.__name__} does not support server-pushed events via events().")
        return


    @abstractmethod
    async def request_and_download_stream(
        self, 
        stream_request_params: Dict[str, Any],
        target_agent_id: str
    ) -> AsyncIterator[bytes]: # pragma: no cover
        """
        Requests a stream download from the server and then streams the data.
        This typically involves a two-step process:
        1. An RPC call to initiate the stream download and get a download URL.
        2. An HTTP GET request to the download URL to fetch the stream.

        Args:
            stream_request_params: Parameters for the REQUEST_STREAM_DOWNLOAD RPC call,
                                   e.g., `{"resource_id": "some_file"}`.
            target_agent_id: The ID of the target agent on the server that owns/provides the stream.
                             This is used to construct the `target_agent_id` field in the RPC request params.

        Yields:
            bytes: Chunks of the downloaded data.

        Raises:
            ConnectionError: If not connected or if communication fails.
            ValueError: If the server response for stream initiation is invalid.
            NotImplementedError: If the connection type does not support this.
        """
        # Default implementation for connection types that don't support this.
        if False: # Makes it an async generator
            yield b'' 
        logger.warning(f"Connection type {self.__class__.__name__} does not support request_and_download_stream().")
        raise NotImplementedError(f"{self.__class__.__name__} does not support stream downloads.")


    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} server_id='{self.server_id}', connected={self.is_connected}>"

