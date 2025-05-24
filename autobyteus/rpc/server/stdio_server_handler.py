# file: autobyteus/autobyteus/rpc/server/stdio_server_handler.py
import asyncio
import sys
import json
import logging
from typing import Dict, Optional, Union

from autobyteus.rpc.protocol import ProtocolMessage, MessageType, ErrorCode, RequestType
from autobyteus.rpc.server.base_method_handler import BaseMethodHandler
from autobyteus.agent.agent import Agent # Changed from AgentRuntime

logger = logging.getLogger(__name__)

class StdioServerHandler:
    """
    Handles RPC communication over stdio for an Agent Server.
    Reads newline-delimited JSON ProtocolMessages from stdin, dispatches them
    to appropriate method handlers (which operate on an Agent instance),
    and writes responses to stdout.
    """

    def __init__(self, agent: Agent, method_handlers: Dict[Union[RequestType, str], BaseMethodHandler]): # Changed runtime to agent
        """
        Initializes the StdioServerHandler.

        Args:
            agent: The Agent instance this server handler is serving.
            method_handlers: A dictionary mapping method names (RequestType or str)
                             to their handler instances.
        """
        self._agent = agent # Changed from _runtime to _agent
        self._method_handlers = method_handlers
        self._running = False
        logger.info(f"StdioServerHandler initialized for agent '{self._agent.agent_id}'.") # Use agent.agent_id

    async def listen_and_dispatch(self) -> None:
        """
        Starts listening on stdin for requests and dispatches them.
        This method runs indefinitely until stdin is closed or an error occurs.
        """
        self._running = True
        logger.info(f"StdioServerHandler for agent '{self._agent.agent_id}' now listening on stdin.")
        
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader(loop=loop)
        protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        try:
            while self._running:
                line_bytes = await reader.readline()
                if not line_bytes:
                    logger.info(f"StdioServerHandler for agent '{self._agent.agent_id}': stdin EOF reached. Shutting down.")
                    self._running = False
                    break
                
                line_str = line_bytes.decode().strip()
                if not line_str:
                    continue

                request_id: Optional[str] = None
                try:
                    try:
                        parsed_json = json.loads(line_str)
                        request_id = parsed_json.get("id")
                    except json.JSONDecodeError:
                        pass

                    message = ProtocolMessage.from_json_str(line_str)
                    request_id = message.id 

                    if message.type == MessageType.REQUEST:
                        response_message = await self._process_request(message)
                    else:
                        logger.warning(f"StdioServerHandler received non-REQUEST message type: {message.type}. Ignoring.")
                        response_message = ProtocolMessage.create_error_response(
                            id=request_id,
                            code=ErrorCode.INVALID_REQUEST,
                            message="Server only accepts REQUEST messages via stdio."
                        )
                    
                    await self._send_response(response_message)

                except json.JSONDecodeError as e:
                    logger.error(f"StdioServerHandler: JSONDecodeError: {e}. Raw line: '{line_str[:200]}'")
                    err_response = ProtocolMessage.create_error_response(
                        id=request_id,
                        code=ErrorCode.PARSE_ERROR,
                        message=f"Failed to parse JSON request: {e}"
                    )
                    await self._send_response(err_response)
                except ValueError as e:
                    logger.error(f"StdioServerHandler: ProtocolMessage validation error: {e}. Raw line: '{line_str[:200]}'")
                    err_response = ProtocolMessage.create_error_response(
                        id=request_id,
                        code=ErrorCode.INVALID_REQUEST,
                        message=f"Invalid request structure: {e}"
                    )
                    await self._send_response(err_response)
                except Exception as e:
                    logger.error(f"StdioServerHandler: Unexpected error processing line: {e}. Raw line: '{line_str[:200]}'", exc_info=True)
                    err_response = ProtocolMessage.create_error_response(
                        id=request_id,
                        code=ErrorCode.INTERNAL_ERROR,
                        message=f"Internal server error: {e}"
                    )
                    await self._send_response(err_response)
        
        except asyncio.CancelledError:
            logger.info(f"StdioServerHandler for agent '{self._agent.agent_id}' listen_and_dispatch task cancelled.")
        except Exception as e:
            logger.error(f"StdioServerHandler for agent '{self._agent.agent_id}' fatal error in listen_and_dispatch: {e}", exc_info=True)
        finally:
            self._running = False
            logger.info(f"StdioServerHandler for agent '{self._agent.agent_id}' stopped listening.")

    async def _process_request(self, request_message: ProtocolMessage) -> ProtocolMessage:
        if not request_message.method:
            logger.warning(f"StdioServerHandler: Request message missing 'method'. ID: {request_message.id}")
            return ProtocolMessage.create_error_response(
                id=request_message.id,
                code=ErrorCode.INVALID_REQUEST,
                message="Request message must include a 'method'."
            )

        handler = self._method_handlers.get(request_message.method)
        if not handler:
            logger.warning(f"StdioServerHandler: No handler found for method '{request_message.method}'. ID: {request_message.id}")
            return ProtocolMessage.create_error_response(
                id=request_message.id,
                code=ErrorCode.METHOD_NOT_FOUND,
                message=f"Method '{request_message.method}' not found."
            )
        
        logger.debug(f"StdioServerHandler dispatching method '{request_message.method}' (ID: {request_message.id}) to {handler.__class__.__name__}.")
        return await handler.handle(request_message.id, request_message.params, self._agent) # Pass self._agent

    async def _send_response(self, response_message: ProtocolMessage) -> None:
        try:
            json_response = response_message.to_json_str()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: sys.stdout.write(json_response + '\n'))
            await loop.run_in_executor(None, sys.stdout.flush)
            logger.debug(f"StdioServerHandler sent response (ID: {response_message.id}, Type: {response_message.type}).")
        except Exception as e:
            logger.error(f"StdioServerHandler failed to send response: {e}", exc_info=True)

    def stop(self):
        logger.info(f"StdioServerHandler for agent '{self._agent.agent_id}' stop requested.")
        self._running = False

