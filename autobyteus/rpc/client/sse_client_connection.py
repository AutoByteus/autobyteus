# file: autobyteus/autobyteus/rpc/client/sse_client_connection.py
import asyncio
import logging
import json
from typing import Optional, AsyncIterator, Dict, Any # Added Dict, Any

import aiohttp
from aiohttp_sse_client.client import EventSource # type: ignore

from autobyteus.rpc.protocol import ProtocolMessage, MessageType, ErrorCode, EventType, RequestType, ResponseType # Added RequestType, ResponseType
from .abstract_client_connection import AbstractClientConnection
from autobyteus.rpc.config import AgentServerConfig, TransportType # Added TransportType from config

logger = logging.getLogger(__name__)

DEFAULT_SSE_TIMEOUT = 30.0  # seconds for an HTTP request response
DEFAULT_SSE_RECONNECTION_TIME = 5 # seconds
DEFAULT_STREAM_DOWNLOAD_TIMEOUT = 300.0 # 5 minutes for stream download requests

class SseClientConnection(AbstractClientConnection):
    """
    Client connection implementation for SSE-based Agent Servers.
    Uses aiohttp for HTTP requests and aiohttp-sse-client for consuming SSE event streams.
    Also supports direct HTTP stream downloads.
    """

    def __init__(self, server_config: AgentServerConfig):
        """
        Initializes the SseClientConnection.

        Args:
            server_config: The configuration for the SSE server.

        Raises:
            ValueError: If server_config is not for SSE or base URL is missing.
        """
        if server_config.transport_type != TransportType.SSE: # Use Enum member
            raise ValueError("SseClientConnection requires an AgentServerConfig with transport_type 'sse'.")
        if not server_config.sse_base_url:
            raise ValueError("AgentServerConfig for sse transport must have an sse_base_url.")

        super().__init__(server_id=server_config.server_id)
        self.server_config: AgentServerConfig = server_config
        self._session: Optional[aiohttp.ClientSession] = None
        self._event_source: Optional[EventSource] = None

    async def connect(self) -> None:
        """
        Establishes the aiohttp ClientSession. For SSE, actual connection
        to event stream happens when events() is iterated.
        """
        async with self._connection_lock:
            if self._is_connected and self._session and not self._session.closed:
                logger.debug(f"SseClientConnection to '{self.server_id}' session already active.")
                return

            try:
                # Create a new session if it doesn't exist or is closed
                if not self._session or self._session.closed:
                    self._session = aiohttp.ClientSession()
                    logger.info(f"SseClientConnection to '{self.server_id}': new aiohttp.ClientSession created.")
                
                self._is_connected = True # Mark as connected once session is ready
                logger.info(f"SseClientConnection to '{self.server_id}' connected (session ready).")
            except Exception as e:
                logger.error(f"Failed to create/ensure aiohttp.ClientSession for '{self.server_id}': {e}", exc_info=True)
                self._is_connected = False
                if self._session and not self._session.closed:
                    await self._session.close()
                self._session = None
                raise ConnectionError(f"Failed to initialize HTTP session for SSE server '{self.server_id}': {e}") from e

    async def close(self) -> None:
        """Closes the aiohttp ClientSession and any active EventSource."""
        async with self._connection_lock:
            if not self._is_connected and not self._session: # Check both state and session object
                logger.debug(f"SseClientConnection to '{self.server_id}' already closed or never connected.")
                return
            
            self._is_connected = False 

            if self._event_source:
                try:
                    await self._event_source.close()
                    logger.debug(f"EventSource for '{self.server_id}' closed.")
                except Exception as e:
                    logger.error(f"Error closing EventSource for '{self.server_id}': {e}", exc_info=True)
                self._event_source = None

            if self._session and not self._session.closed:
                try:
                    await self._session.close()
                    logger.debug(f"aiohttp.ClientSession for '{self.server_id}' closed.")
                except Exception as e:
                    logger.error(f"Error closing aiohttp.ClientSession for '{self.server_id}': {e}", exc_info=True)
            self._session = None # Ensure session object is cleared
            
            logger.info(f"SseClientConnection to '{self.server_id}' closed.")

    async def send_request(self, request_message: ProtocolMessage) -> ProtocolMessage:
        """Sends a request via HTTP POST and awaits a JSON response."""
        if not self._is_connected or not self._session or self._session.closed:
            logger.info(f"SseClientConnection '{self.server_id}' not connected or session closed/missing. Attempting to connect before send_request.")
            await self.connect() 
            if not self._is_connected or not self._session or self._session.closed: # Check again after connect attempt
                raise ConnectionError(f"Failed to connect to SSE server '{self.server_id}' for send_request (connection attempt failed).")

        if request_message.type != MessageType.REQUEST:
            raise ValueError("ProtocolMessage must be of type REQUEST to be sent via send_request.")
        if not request_message.id:
            raise ValueError("Request ProtocolMessage must have an ID.")

        request_url = self.server_config.get_sse_full_request_url()
        if not request_url: 
            raise ValueError("SSE request URL is not configured.")

        logger.debug(f"SseClient '{self.server_id}' sending request to {request_url}: {request_message.to_json_str()}")
        
        try:
            async with self._session.post(
                request_url,
                json=request_message.model_dump(exclude_none=True), 
                timeout=DEFAULT_SSE_TIMEOUT
            ) as response:
                response_text = await response.text()
                if response.status >= 200 and response.status < 300:
                    try:
                        return ProtocolMessage.from_json_str(response_text)
                    except (json.JSONDecodeError, ValueError) as e: 
                        logger.error(f"Error decoding JSON response from '{request_url}': {e}. Response text: {response_text[:200]}")
                        return ProtocolMessage.create_error_response(
                            id=request_message.id,
                            code=ErrorCode.PARSE_ERROR,
                            message=f"Failed to parse JSON response from server: {e}"
                        )
                else:
                    logger.error(f"HTTP error from '{request_url}': {response.status} {response.reason}. Response: {response_text[:200]}")
                    return ProtocolMessage.create_error_response(
                        id=request_message.id,
                        code=ErrorCode.INTERNAL_ERROR, 
                        message=f"Server returned HTTP error {response.status}: {response.reason}. Body: {response_text[:200]}"
                    )
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error for '{request_url}': {e}", exc_info=True)
            await self.close() # Connection is likely broken, perform full close
            raise ConnectionError(f"Could not connect to SSE server at '{request_url}': {e}") from e
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending request to '{request_url}' for ID '{request_message.id}'.")
            # Don't necessarily close connection on timeout, server might be slow.
            return ProtocolMessage.create_error_response(
                id=request_message.id,
                code=ErrorCode.SERVER_ERROR_TIMEOUT,
                message=f"Timeout waiting for response from SSE server for request ID '{request_message.id}'."
            )
        except Exception as e:
            logger.error(f"Unexpected error sending request to '{request_url}': {e}", exc_info=True)
            if isinstance(e, (aiohttp.ClientError)): 
                 await self.close() # If it's a client lib error, connection might be compromised
            return ProtocolMessage.create_error_response(
                id=request_message.id,
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Client-side error sending request: {e}"
            )

    async def events(self) -> AsyncIterator[ProtocolMessage]:
        """Connects to the SSE event stream and yields ProtocolMessages."""
        if not self._is_connected or not self._session or self._session.closed:
            logger.info(f"SseClientConnection '{self.server_id}' session not found or closed, attempting to connect before streaming events.")
            await self.connect()
            if not self._is_connected or not self._session or self._session.closed: # Check again
                 raise ConnectionError(f"Not connected to SSE server '{self.server_id}' for event streaming (connection attempt failed).")

        # Construct event URL. Note: SseServerHandler expects /events/{agent_id_on_server}
        # The client config's server_id typically maps to an agent_id_on_server or is the agent_id_on_server.
        # For multi-agent servers, the client needs to know which agent_id_on_server to subscribe to.
        # This implies server_config.server_id is the agent_id_on_server for SSE event subscriptions.
        base_events_url = self.server_config.get_sse_full_events_url()
        if not base_events_url: # This is base path like /events
             raise ValueError("SSE events base URL path is not configured.")
        
        # Assuming self.server_id (from config) is the key for the agent on the server.
        events_url = f"{base_events_url.rstrip('/')}/{self.server_id}"
        logger.info(f"SseClient '{self.server_id}' connecting to event stream at {events_url}")
        
        if self._event_source: # Close existing if any
            await self._event_source.close()
            self._event_source = None

        try:
            self._event_source = EventSource(
                events_url,
                session=self._session, # Use existing session
                reconnection_time=DEFAULT_SSE_RECONNECTION_TIME,
            )
            await self._event_source.connect() 

            async for sse_event in self._event_source:
                try:
                    logger.debug(f"SseClient '{self.server_id}' received SSE event data: {sse_event.data[:200]}")
                    msg = ProtocolMessage.from_json_str(sse_event.data)
                    if msg.type == MessageType.EVENT:
                        yield msg
                    else:
                        logger.warning(f"Received non-EVENT ProtocolMessage via SSE stream: {msg.type}. Ignoring.")
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from SSE event data: {e}. Data: {sse_event.data[:200]}")
                except ValueError as e: 
                    logger.error(f"Error validating ProtocolMessage from SSE event data: {e}. Data: {sse_event.data[:200]}")
                except Exception as e:
                    logger.error(f"Error processing SSE event: {e}", exc_info=True)

        except ConnectionRefusedError as e:
            logger.error(f"SSE EventStream for '{self.server_id}' connection refused at {events_url}: {e}")
            await self.close()
            raise ConnectionError(f"SSE EventStream connection refused: {e}") from e
        except aiohttp.ClientError as e: 
            logger.error(f"SSE EventStream client error for '{self.server_id}' at {events_url}: {e}", exc_info=True)
            await self.close() 
            raise ConnectionError(f"SSE EventStream client error: {e}") from e
        except asyncio.CancelledError:
            logger.info(f"SSE event stream for '{self.server_id}' cancelled.")
            if self._event_source: await self._event_source.close()
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SSE event stream for '{self.server_id}': {e}", exc_info=True)
            if self._event_source: await self._event_source.close()
            await self.close()
            raise ConnectionError(f"Unexpected error in SSE event stream: {e}") from e
        finally:
            logger.info(f"SseClient '{self.server_id}' event stream iteration finished.")
            if self._event_source: 
                await self._event_source.close()
                self._event_source = None


    async def request_and_download_stream(
        self, 
        stream_request_params: Dict[str, Any],
        target_agent_id: str # This is the agent_id_on_server key
    ) -> AsyncIterator[bytes]:
        """
        Requests a stream download via RPC and then downloads the stream via HTTP GET.
        """
        if not self._is_connected or not self._session or self._session.closed:
            logger.info(f"SseClientConnection '{self.server_id}' not connected or session closed/missing. Attempting to connect before stream download.")
            await self.connect()
            if not self._is_connected or not self._session or self._session.closed:
                raise ConnectionError(f"Failed to connect to SSE server '{self.server_id}' for stream download (connection attempt failed).")

        # Step 1: RPC call to initiate stream download
        # The target_agent_id for the stream must be included in the params for the RPC call.
        rpc_params = {**stream_request_params, "target_agent_id": target_agent_id}
        initiate_request_msg = ProtocolMessage.create_request(
            method=RequestType.REQUEST_STREAM_DOWNLOAD,
            params=rpc_params
        )
        
        logger.debug(f"SseClient '{self.server_id}' sending stream download initiation request for target_agent_id '{target_agent_id}': {initiate_request_msg.to_json_str()}")
        
        initiate_response_msg = await self.send_request(initiate_request_msg)

        if initiate_response_msg.type == MessageType.ERROR or not initiate_response_msg.result:
            err_details = initiate_response_msg.error.message if initiate_response_msg.error else "Unknown error"
            logger.error(f"Failed to initiate stream download for target_agent_id '{target_agent_id}'. Server error: {err_details}")
            raise ValueError(f"Server error initiating stream download: {err_details}")

        if initiate_response_msg.response_type != ResponseType.STREAM_DOWNLOAD_READY:
            logger.error(f"Unexpected response type from stream download initiation: {initiate_response_msg.response_type}")
            raise ValueError(f"Unexpected response type: {initiate_response_msg.response_type}")

        download_url = initiate_response_msg.result.get("download_url")
        if not download_url:
            logger.error(f"No 'download_url' in STREAM_DOWNLOAD_READY response. Result: {initiate_response_msg.result}")
            raise ValueError("Server response did not include a download_url for the stream.")

        stream_metadata = initiate_response_msg.result.get("metadata", {})
        logger.info(f"SseClient '{self.server_id}' received download URL: {download_url}. Metadata: {stream_metadata}")

        # Step 2: HTTP GET request to the download_url
        try:
            logger.debug(f"SseClient '{self.server_id}' starting GET request to stream from {download_url}")
            async with self._session.get(download_url, timeout=DEFAULT_STREAM_DOWNLOAD_TIMEOUT) as response:
                response.raise_for_status() # Raise an exception for HTTP error codes (4xx or 5xx)
                
                # Stream the content
                async for chunk in response.content.iter_any(): # iter_any() or iter_chunked(chunk_size)
                    yield chunk
                logger.info(f"SseClient '{self.server_id}' finished streaming from {download_url}")

        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP error during stream download from '{download_url}': {e.status} {e.message}", exc_info=True)
            # Connection might still be usable for other RPCs, don't necessarily close.
            raise ConnectionError(f"HTTP error downloading stream: {e.status} {e.message}") from e
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error during stream download from '{download_url}': {e}", exc_info=True)
            await self.close() # Connection likely broken
            raise ConnectionError(f"Could not connect to download stream at '{download_url}': {e}") from e
        except asyncio.TimeoutError:
            logger.warning(f"Timeout downloading stream from '{download_url}'.")
            # Don't close connection, server might be slow or stream very long with no data.
            raise TimeoutError(f"Timeout downloading stream from '{download_url}'.")
        except Exception as e:
            logger.error(f"Unexpected error downloading stream from '{download_url}': {e}", exc_info=True)
            if isinstance(e, (aiohttp.ClientError)):
                 await self.close() # If it's a client lib error, connection might be compromised
            raise ConnectionError(f"Client-side error downloading stream: {e}") from e
