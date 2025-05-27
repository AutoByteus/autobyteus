# file: autobyteus/autobyteus/rpc/client/stdio_client_connection.py
import asyncio
import logging
import json
from typing import List, Optional, Dict, Any, AsyncIterator # Added Any, AsyncIterator

from autobyteus.rpc.protocol import ProtocolMessage, MessageType, ErrorCode
from .abstract_client_connection import AbstractClientConnection
from autobyteus.rpc.config import AgentServerConfig, TransportType # Added TransportType

logger = logging.getLogger(__name__)

DEFAULT_STDIO_TIMEOUT = 10.0  # seconds for a response

class StdioClientConnection(AbstractClientConnection):
    """
    Client connection implementation for stdio-based Agent Servers.
    Manages a subprocess and communicates via its stdin/stdout using
    newline-delimited JSON ProtocolMessages.
    """

    def __init__(self, server_config: AgentServerConfig):
        """
        Initializes the StdioClientConnection.

        Args:
            server_config: The configuration for the stdio server.

        Raises:
            ValueError: If server_config is not for stdio or stdio_command is missing.
        """
        if server_config.transport_type != TransportType.STDIO: # Using Enum member
            raise ValueError("StdioClientConnection requires an AgentServerConfig with transport_type 'stdio'.")
        if not server_config.stdio_command:
            raise ValueError("AgentServerConfig for stdio transport must have a stdio_command.")

        super().__init__(server_id=server_config.server_id)
        self.server_config: AgentServerConfig = server_config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock() # For managing access to _response_futures

    async def connect(self) -> None:
        """
        Starts the stdio server subprocess and establishes communication.
        """
        async with self._connection_lock:
            if self._is_connected:
                logger.debug(f"StdioClientConnection to '{self.server_id}' already connected.")
                return

            try:
                logger.info(f"Connecting StdioClientConnection to '{self.server_id}' using command: {' '.join(self.server_config.stdio_command)}")
                self._process = await asyncio.create_subprocess_exec(
                    *self.server_config.stdio_command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE 
                )
                self._is_connected = True
                self._reader_task = asyncio.create_task(self._read_loop(), name=f"stdio_reader_{self.server_id}")
                asyncio.create_task(self._log_stderr(), name=f"stdio_stderr_logger_{self.server_id}")
                logger.info(f"StdioClientConnection to '{self.server_id}' connected successfully (PID: {self._process.pid}).")
            except Exception as e:
                logger.error(f"Failed to connect StdioClientConnection to '{self.server_id}': {e}", exc_info=True)
                self._is_connected = False
                if self._process and self._process.returncode is None:
                    self._process.terminate()
                    await self._process.wait()
                self._process = None
                raise ConnectionError(f"Failed to start or connect to stdio server '{self.server_id}': {e}") from e

    async def _log_stderr(self) -> None:
        """Logs stderr from the subprocess."""
        if not self._process or not self._process.stderr:
            return 

        try:
            while self._process.returncode is None: 
                line_bytes = await self._process.stderr.readline()
                if not line_bytes: 
                    if self._process.returncode is not None: 
                        break
                    await asyncio.sleep(0.01) 
                    continue
                
                line_str = line_bytes.decode(errors='replace').strip()
                if line_str: 
                    logger.warning(f"StdioServer '{self.server_id}' stderr: {line_str}")
                
                if self._process.returncode is not None and self._process.stderr.at_eof():
                    break

        except asyncio.CancelledError:
            logger.info(f"Stderr logging for '{self.server_id}' cancelled.")
        except Exception as e:
            logger.error(f"Error in stderr logging for '{self.server_id}': {e}", exc_info=True)
        finally:
            logger.debug(f"Stderr logging task for '{self.server_id}' finished.")


    async def _read_loop(self) -> None:
        """Reads messages from stdout and dispatches them."""
        if not self._process or not self._process.stdout:
            logger.error(f"StdioClientConnection '{self.server_id}' read_loop: Process or stdout not available.")
            return 

        try:
            while self._is_connected and self._process.returncode is None:
                line_bytes = await self._process.stdout.readline()
                if not line_bytes: 
                    logger.info(f"StdioServer '{self.server_id}' stdout EOF reached. Process likely terminated.")
                    if self._is_connected: 
                        await self._handle_unexpected_disconnect()
                    break
                
                line_str = line_bytes.decode().strip()
                if not line_str: 
                    continue

                try:
                    message = ProtocolMessage.from_json_str(line_str)
                    if message.id and message.id in self._response_futures:
                        future = self._response_futures.pop(message.id, None)
                        if future and not future.done():
                            future.set_result(message)
                        elif future and future.done():
                             logger.warning(f"Future for response ID '{message.id}' was already done. Duplicate response or late arrival?")
                    elif message.type == MessageType.EVENT:
                        logger.info(f"Received EVENT message via stdio (unexpected for this model): {message}")
                    else:
                        logger.warning(f"Received stdio message with no matching future or unhandled type: {message}")
                except (json.JSONDecodeError, ValueError) as e: 
                    logger.error(f"Failed to parse ProtocolMessage from stdio server '{self.server_id}': {e}. Line: '{line_str[:200]}'")
                except Exception as e:
                    logger.error(f"Unexpected error processing message from stdio server '{self.server_id}': {e}. Line: '{line_str[:200]}'", exc_info=True)

        except asyncio.CancelledError:
            logger.info(f"Stdio read_loop for '{self.server_id}' cancelled.")
        except Exception as e:
            logger.error(f"Fatal error in stdio read_loop for '{self.server_id}': {e}", exc_info=True)
            if self._is_connected: 
                self._handle_unexpected_disconnect()
        finally:
            logger.info(f"Stdio read_loop for '{self.server_id}' exiting.")
            if self._is_connected:
                await self._handle_unexpected_disconnect(log_warning=False) 

    async def _handle_unexpected_disconnect(self, log_warning=True):
        """Handles unexpected disconnection by failing pending futures."""
        if log_warning:
            logger.warning(f"StdioClientConnection to '{self.server_id}'  unexpectedly disconnected or process terminated.")
        self._is_connected = False 
        
        # Error response is not used here, futures are set with specific errors
        # error_response = ProtocolMessage.create_error_response(...)
        async with self._lock:
            for msg_id, future in list(self._response_futures.items()): 
                if not future.done():
                    custom_error = ProtocolMessage.create_error_response(
                        id=msg_id, code=ErrorCode.INTERNAL_ERROR, 
                        message=f"Connection lost before response for request ID {msg_id} was received."
                    )
                    future.set_result(custom_error) 
                self._response_futures.pop(msg_id, None)


    async def close(self) -> None:
        """Closes the connection and terminates the subprocess."""
        async with self._connection_lock:
            if not self._is_connected and not self._process:
                logger.debug(f"StdioClientConnection to '{self.server_id}' already closed or never connected.")
                return

            self._is_connected = False 

            if self._reader_task and not self._reader_task.done():
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass 
            self._reader_task = None
            
            error_on_close = ProtocolMessage.create_error_response(
                id=None, code=ErrorCode.INTERNAL_ERROR, message="Connection closed by client while request was pending."
            )
            for msg_id, future in list(self._response_futures.items()):
                if not future.done():
                    custom_error = ProtocolMessage.create_error_response(
                        id=msg_id, code=ErrorCode.INTERNAL_ERROR,
                        message=f"Connection closed for request ID {msg_id} before response."
                    )
                    future.set_result(custom_error)
                self._response_futures.pop(msg_id, None)


            if self._process:
                if self._process.returncode is None: 
                    logger.info(f"Terminating stdio server process for '{self.server_id}' (PID: {self._process.pid}).")
                    try:
                        self._process.terminate()
                        await asyncio.wait_for(self._process.wait(), timeout=DEFAULT_STDIO_TIMEOUT / 2)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout terminating stdio server '{self.server_id}'. Killing process.")
                        if self._process.returncode is None: self._process.kill() # Check again before kill
                        await self._process.wait()
                    except Exception as e: 
                        logger.error(f"Error during stdio server termination for '{self.server_id}': {e}")
                else:
                    logger.info(f"Stdio server process for '{self.server_id}' (PID: {self._process.pid}) already exited with code {self._process.returncode}.")
                self._process = None
            
            logger.info(f"StdioClientConnection to '{self.server_id}' closed.")

    async def send_request(self, request_message: ProtocolMessage) -> ProtocolMessage:
        """Sends a request and waits for a response."""
        if not self._is_connected or not self._process or not self._process.stdin:
            # Attempt to reconnect if not connected
            logger.info(f"StdioClientConnection '{self.server_id}' not connected. Attempting to connect before send_request.")
            await self.connect()
            if not self._is_connected or not self._process or not self._process.stdin:
                raise ConnectionError(f"Failed to connect to stdio server '{self.server_id}' for send_request.")

        if request_message.type != MessageType.REQUEST:
            raise ValueError("ProtocolMessage must be of type REQUEST to be sent via send_request.")
        if not request_message.id: 
            raise ValueError("Request ProtocolMessage must have an ID.")

        future: asyncio.Future[ProtocolMessage] = asyncio.Future()
        async with self._lock:
            self._response_futures[request_message.id] = future

        try:
            json_str = request_message.to_json_str()
            logger.debug(f"StdioClient '{self.server_id}' sending: {json_str}")
            self._process.stdin.write(json_str.encode() + b'\n')
            await self._process.stdin.drain()
        except Exception as e:
            async with self._lock:
                self._response_futures.pop(request_message.id, None) 
            # Don't cancel future, let it timeout or be resolved by _handle_unexpected_disconnect
            logger.error(f"Error sending request to stdio server '{self.server_id}': {e}", exc_info=True)
            # If send fails, connection is likely broken. Mark as such and try to close.
            await self.close()
            raise ConnectionError(f"Failed to send request to stdio server '{self.server_id}': {e}") from e

        try:
            response = await asyncio.wait_for(future, timeout=DEFAULT_STDIO_TIMEOUT)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response to request ID '{request_message.id}' from stdio server '{self.server_id}'.")
            async with self._lock:
                if request_message.id in self._response_futures:
                    self._response_futures.pop(request_message.id, None)
            return ProtocolMessage.create_error_response(
                id=request_message.id,
                code=ErrorCode.SERVER_ERROR_TIMEOUT,
                message=f"Timeout waiting for response to request ID '{request_message.id}'."
            )
        except asyncio.CancelledError: 
            logger.info(f"Request ID '{request_message.id}' was cancelled while awaiting response.")
            return ProtocolMessage.create_error_response(
                id=request_message.id,
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Request ID '{request_message.id}' cancelled."
            )

    async def request_and_download_stream(
        self, 
        stream_request_params: Dict[str, Any],
        target_agent_id: str
    ) -> AsyncIterator[bytes]:
        logger.warning(f"StdioClientConnection does not support HTTP stream downloads for target_agent_id '{target_agent_id}'.")
        raise NotImplementedError("StdioClientConnection does not support HTTP stream downloads.")
        # This construct makes it an async generator that immediately raises
        if False: # pragma: no cover
            yield b''

