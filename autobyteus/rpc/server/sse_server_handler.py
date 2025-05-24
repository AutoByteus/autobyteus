# file: autobyteus/autobyteus/rpc/server/sse_server_handler.py
import asyncio
import logging
import json
from typing import Dict, Optional, Union, Set, cast, AsyncIterator # Added AsyncIterator
from weakref import WeakSet

from aiohttp import web 
from aiohttp_sse import sse_response 

from autobyteus.agent.agent import Agent
from autobyteus.agent.streaming import AgentOutputStreams, StreamEvent as AgentStreamEvent, StreamEventType as AgentStreamEventType
from autobyteus.rpc.protocol import ProtocolMessage, MessageType, ErrorCode, RequestType, ResponseType, EventType as RPCEventType # Added ResponseType
from autobyteus.rpc.server.base_method_handler import BaseMethodHandler
from autobyteus.rpc.config import AgentServerConfig 

logger = logging.getLogger(__name__)

DEFAULT_STREAM_CHUNK_SIZE = 8192 # 8KB chunks for generic stream download

class SseServerHandler:
    """
    Handles RPC communication over HTTP and Server-Sent Events (SSE)
    for an Agent Server, potentially serving multiple agents.
    Also handles direct HTTP stream downloads.
    """
    def __init__(self, agents: Dict[str, Agent], method_handlers: Dict[Union[RequestType, str], BaseMethodHandler]):
        """
        Initializes the SseServerHandler.

        Args:
            agents: A dictionary mapping server-routable agent IDs to Agent instances.
            method_handlers: Dictionary mapping RPC method names to their handlers.
        """
        self._agents: Dict[str, Agent] = agents
        self._method_handlers = method_handlers
        self._app = web.Application()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        
        self._active_sse_forwarding_tasks: Dict[web.StreamResponse, asyncio.Task] = {}

        logger.info(f"SseServerHandler initialized to serve agents: {list(self._agents.keys())}.")

    def _setup_routes(self, config: AgentServerConfig):
        rpc_request_path = config.sse_request_endpoint
        base_events_path = config.sse_events_endpoint.rstrip('/')
        full_events_path = f"{base_events_path}/{{agent_id_on_server}}"

        stream_download_prefix = config.sse_stream_download_path_prefix.rstrip('/')
        # Path: /streams/{agent_id_on_server}/{stream_id}
        full_stream_download_path = f"{stream_download_prefix}/{{agent_id_on_server}}/{{stream_id}}"


        self._app.router.add_post(rpc_request_path, self.handle_rpc_request)
        self._app.router.add_get(full_events_path, self.handle_sse_events_subscription)
        self._app.router.add_get(full_stream_download_path, self.handle_http_stream_download)

        logger.info(f"SseServerHandler routes: POST {rpc_request_path} (RPC), GET {full_events_path} (SSE per agent), GET {full_stream_download_path} (HTTP Stream Download).")

    async def handle_rpc_request(self, http_request: web.Request) -> web.Response:
        request_id: Optional[str] = None
        raw_body_str: str = ""
        target_agent_id: Optional[str] = None # Keep track of the resolved agent_id_on_server

        try:
            raw_body = await http_request.read()
            raw_body_str = raw_body.decode()
            
            # Early parse for ID and target_agent_id if possible
            try:
                parsed_json_early = json.loads(raw_body_str) 
                request_id = parsed_json_early.get("id")
            except json.JSONDecodeError: # Will be caught later properly
                pass
            
            request_message = ProtocolMessage.from_json_str(raw_body_str)
            request_id = request_message.id # Ensure request_id is from parsed message

            if request_message.type != MessageType.REQUEST or not request_message.method:
                return self._create_json_error_response(request_id, ErrorCode.INVALID_REQUEST, "Must be REQUEST with method.", 400)

            # Extract target_agent_id for routing if it's part of standard RPC params
            # For InvokeMethod, it's in params. For DiscoverCapabilities, also in params.
            # For RequestStreamDownload, also in params.
            if request_message.params and "target_agent_id" in request_message.params:
                target_agent_id = str(request_message.params["target_agent_id"])
            
            if not target_agent_id:
                # Some methods might not require target_agent_id if they are server-global.
                # For now, assume all handled methods are agent-specific.
                return self._create_json_error_response(request_id, ErrorCode.INVALID_PARAMS, "'target_agent_id' missing in request params.", 400)

            target_agent = self._agents.get(target_agent_id)
            if not target_agent:
                return self._create_json_error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"Agent with id '{target_agent_id}' not found on this server.", 404)

            actual_handler_params = request_message.params
            
            handler = self._method_handlers.get(request_message.method)
            if not handler:
                return self._create_json_error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"RPC Method '{request_message.method}' not found.", 404)

            logger.debug(f"SseServerHandler dispatching RPC method '{request_message.method}' (ReqID: {request_id}) to handler '{handler.__class__.__name__}' for target agent '{target_agent_id}'.")
            response_proto = await handler.handle(request_id, actual_handler_params, target_agent) 
            
            # If the response is for a stream download, construct the full download URL
            if response_proto.response_type == ResponseType.STREAM_DOWNLOAD_READY and \
               response_proto.result and \
               "stream_id" in response_proto.result and \
               target_agent_id: # target_agent_id is the agent_id_on_server

                server_config: AgentServerConfig = http_request.app['agent_server_config']
                # base_url_for_stream = str(server_config.sse_base_url).rstrip('/') # From config
                # stream_prefix = server_config.sse_stream_download_path_prefix.rstrip('/')
                # stream_id = response_proto.result["stream_id"]
                # download_url = f"{base_url_for_stream}{stream_prefix}/{target_agent_id}/{stream_id}"
                
                # Use helper from AgentServerConfig
                full_url_prefix = server_config.get_sse_full_stream_download_url_prefix_for_agent(target_agent_id)
                if full_url_prefix:
                    stream_id = response_proto.result["stream_id"]
                    download_url = f"{full_url_prefix.rstrip('/')}/{stream_id}"
                    response_proto.result["download_url"] = download_url
                    logger.info(f"Constructed download URL for stream_id '{stream_id}': {download_url}")
                else:
                    logger.error(f"Could not construct download_url for stream_id '{response_proto.result['stream_id']}' due to missing URL components in config.")
                    # Potentially convert to an error response or log and send as is
                    # For now, let's assume config is correct.

            http_status = 200
            if response_proto.type == MessageType.ERROR and response_proto.error:
                if response_proto.error.code == ErrorCode.METHOD_NOT_FOUND.value: http_status = 404
                elif response_proto.error.code in [ErrorCode.INVALID_REQUEST.value, ErrorCode.INVALID_PARAMS.value, ErrorCode.PARSE_ERROR.value]: http_status = 400
                else: http_status = 500
            
            return web.json_response(response_proto.model_dump(exclude_none=True), status=http_status)

        except json.JSONDecodeError as e:
            logger.error(f"SseServerHandler JSONDecodeError: {e}. Raw body: '{raw_body_str[:200]}'")
            return self._create_json_error_response(request_id, ErrorCode.PARSE_ERROR, f"Failed to parse JSON: {e}", 400)
        except ValueError as e: 
            logger.error(f"SseServerHandler ProtocolMessage validation error: {e}. Raw body: '{raw_body_str[:200]}'")
            return self._create_json_error_response(request_id, ErrorCode.INVALID_REQUEST, f"Invalid request: {e}", 400)
        except Exception as e:
            logger.error(f"SseServerHandler unexpected error processing RPC request: {e}", exc_info=True)
            return self._create_json_error_response(request_id, ErrorCode.INTERNAL_ERROR, f"Internal server error: {e}", 500)

    def _create_json_error_response(self, req_id: Optional[str], code: ErrorCode, msg: str, http_status: int) -> web.Response:
        err_proto = ProtocolMessage.create_error_response(req_id, code, msg)
        return web.json_response(err_proto.model_dump(exclude_none=True), status=http_status)

    async def handle_sse_events_subscription(self, http_request: web.Request) -> web.StreamResponse:
        agent_id_on_server = http_request.match_info.get("agent_id_on_server")
        if not agent_id_on_server:
            logger.warning("SSE subscription request missing 'agent_id_on_server' in path.")
            raise web.HTTPBadRequest(text="agent_id_on_server path parameter is required for SSE event stream.")

        target_agent = self._agents.get(agent_id_on_server)
        if not target_agent:
            logger.warning(f"SSE subscription request for unknown agent_id_on_server: '{agent_id_on_server}'.")
            raise web.HTTPNotFound(text=f"Agent with server ID '{agent_id_on_server}' not found.")

        client_addr = http_request.remote
        logger.info(f"SSE client {client_addr} subscribing to events for agent '{target_agent.agent_id}' (server key: '{agent_id_on_server}').")

        sse_resp = web.StreamResponse(
            status=200,
            reason='OK',
            headers={'Content-Type': 'text/event-stream',
                     'Cache-Control': 'no-cache',
                     'Connection': 'keep-alive'}
        )
        await sse_resp.prepare(http_request) 

        forwarding_task = asyncio.create_task(
            self._stream_agent_events_to_client(sse_resp, target_agent),
            name=f"sse_forwarder_{target_agent.agent_id}_{client_addr}"
        )
        self._active_sse_forwarding_tasks[sse_resp] = forwarding_task

        try:
            await forwarding_task 
        except asyncio.CancelledError:
            logger.info(f"SSE event streaming task for agent '{target_agent.agent_id}' to {client_addr} was cancelled.")
        except Exception as e:
            logger.error(f"Error in SSE event streaming for agent '{target_agent.agent_id}' to {client_addr}: {e}", exc_info=True)
        finally:
            logger.info(f"SSE client {client_addr} for agent '{target_agent.agent_id}' disconnected.")
            self._active_sse_forwarding_tasks.pop(sse_resp, None)
        return sse_resp


    async def _stream_agent_events_to_client(self, sse_client_resp: web.StreamResponse, agent: Agent):
        """Streams events from a specific agent to a single connected SSE client."""
        if not agent.context:
            logger.error(f"SseServerHandler: Agent '{agent.agent_id}' context is None. Cannot stream events.")
            return
        agent_queues = agent.get_event_queues()
        if not agent_queues:
            logger.error(f"SseServerHandler: Agent '{agent.agent_id}' event queues not available. Cannot stream events.")
            return

        output_streams = AgentOutputStreams(agent_queues, agent.agent_id)
        logger.debug(f"SseServerHandler: Started event streaming from agent '{agent.agent_id}' to a client.")
        
        try:
            async for agent_event in output_streams.stream_unified_agent_events():
                if sse_client_resp.closed: break

                rpc_event_type: RPCEventType
                if agent_event.event_type == AgentStreamEventType.ASSISTANT_CHUNK: rpc_event_type = RPCEventType.AGENT_OUTPUT_CHUNK
                elif agent_event.event_type == AgentStreamEventType.ASSISTANT_FINAL_MESSAGE: rpc_event_type = RPCEventType.AGENT_FINAL_MESSAGE
                elif agent_event.event_type == AgentStreamEventType.TOOL_INTERACTION_LOG_ENTRY: rpc_event_type = RPCEventType.TOOL_LOG_ENTRY
                elif agent_event.event_type == AgentStreamEventType.AGENT_STATUS_CHANGE: rpc_event_type = RPCEventType.AGENT_STATUS_UPDATE
                else: rpc_event_type = RPCEventType.AGENT_STATUS_UPDATE 
                
                payload_data = {"agent_id": agent_event.agent_id, **agent_event.data}
                payload_data["server_key_agent_id"] = agent.agent_id 

                protocol_event_msg = ProtocolMessage.create_event(event_type=rpc_event_type, payload=payload_data)
                
                try:
                    sse_event_str = f"event: {str(protocol_event_msg.event_type)}\ndata: {protocol_event_msg.to_json_str()}\n\n"
                    await sse_client_resp.write(sse_event_str.encode())
                except ConnectionResetError:
                    logger.info(f"SSE client connection reset while sending event for agent '{agent.agent_id}'. Stream ending.")
                    break
                except Exception as send_e:
                    logger.error(f"Error sending SSE event for agent '{agent.agent_id}': {send_e}")
                    break 

            if not sse_client_resp.closed: 
                await sse_client_resp.write_eof()

        except asyncio.CancelledError:
            logger.info(f"Event streaming for agent '{agent.agent_id}' to a client was cancelled.")
        except Exception as e:
            logger.error(f"Error in event streaming for agent '{agent.agent_id}': {e}", exc_info=True)
        finally:
            logger.debug(f"Finished event streaming from agent '{agent.agent_id}' to a client.")


    async def handle_http_stream_download(self, http_request: web.Request) -> web.StreamResponse:
        """Handles direct HTTP GET requests for streaming data."""
        agent_id_on_server = http_request.match_info.get("agent_id_on_server")
        stream_id = http_request.match_info.get("stream_id")

        if not agent_id_on_server or not stream_id:
            logger.warning("HTTP stream download request missing 'agent_id_on_server' or 'stream_id' in path.")
            raise web.HTTPBadRequest(text="agent_id_on_server and stream_id path parameters are required.")

        target_agent = self._agents.get(agent_id_on_server)
        if not target_agent:
            logger.warning(f"HTTP stream download request for unknown agent_id_on_server: '{agent_id_on_server}'.")
            # Respond with a ProtocolMessage error? Or plain HTTP error? Plain HTTP for now.
            raise web.HTTPNotFound(text=f"Agent with server ID '{agent_id_on_server}' not found.")

        logger.info(f"HTTP stream download request for agent '{target_agent.agent_id}' (server key: '{agent_id_on_server}'), stream_id '{stream_id}'.")

        if not hasattr(target_agent, "get_stream_data") or not hasattr(target_agent, "cleanup_stream_resource"):
            logger.error(f"Agent '{target_agent.agent_id}' does not implement 'get_stream_data' and/or 'cleanup_stream_resource' required for HTTP streaming.")
            raise web.HTTPNotImplemented(text=f"Agent '{target_agent.agent_id}' does not support stream data retrieval.")

        try:
            # Retrieve the data iterator from the agent
            # This agent method is conceptual
            data_iterator: AsyncIterator[bytes] = await target_agent.get_stream_data(stream_id)
            
            # Prepare stream response
            # TODO: Get Content-Type from metadata if available, or make it configurable.
            # For now, use application/octet-stream.
            # Metadata might have been returned by `prepare_resource_for_streaming` and stored by client/passed back.
            # Or Agent could provide it with get_stream_data.
            # Let's assume metadata (like filename for Content-Disposition) comes from agent.
            # For simplicity now, just stream bytes.
            response = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "application/octet-stream", # Or determine from metadata
                    # "Content-Disposition": f'attachment; filename="{metadata.get("filename", stream_id)}"' # Example
                }
            )
            await response.prepare(http_request)

            async for chunk in data_iterator:
                if not isinstance(chunk, bytes):
                    logger.error(f"Agent '{target_agent.agent_id}' stream_id '{stream_id}' yielded non-bytes data: {type(chunk)}. Stopping stream.")
                    # TODO: signal error to client if possible, or just close
                    break 
                await response.write(chunk)
                await asyncio.sleep(0) # Yield control, important for heavily blocking iterators

            await response.write_eof() # Finalize the response stream
            logger.info(f"Successfully streamed data for agent '{target_agent.agent_id}', stream_id '{stream_id}'.")
            return response

        except FileNotFoundError: # Example: if agent.get_stream_data signals not found
            logger.warning(f"Stream_id '{stream_id}' not found for agent '{target_agent.agent_id}'.")
            raise web.HTTPNotFound(text=f"Stream resource '{stream_id}' not found.")
        except asyncio.CancelledError:
            logger.info(f"HTTP stream download for stream_id '{stream_id}' (agent '{target_agent.agent_id}') cancelled by client.")
            raise # Re-raise to ensure connection cleanup
        except Exception as e:
            logger.error(f"Error during HTTP stream download for stream_id '{stream_id}' (agent '{target_agent.agent_id}'): {e}", exc_info=True)
            # Return a generic server error
            raise web.HTTPInternalServerError(text="Error serving stream data.")
        finally:
            # Ensure agent cleans up resources for this stream
            try:
                await target_agent.cleanup_stream_resource(stream_id)
                logger.debug(f"Agent '{target_agent.agent_id}' cleaned up resources for stream_id '{stream_id}'.")
            except Exception as cleanup_e:
                logger.error(f"Error during agent cleanup for stream_id '{stream_id}': {cleanup_e}", exc_info=True)


    async def start_server(self, config: AgentServerConfig) -> None:
        if not config.sse_base_url:
            raise ValueError("SSE base URL is required to start SseServerHandler.")
        
        self._app['agent_server_config'] = config # Store config for access in handlers
        self._setup_routes(config)
        
        host = config.sse_base_url.host or "0.0.0.0"
        port = config.sse_base_url.port or 80

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host, port)
        
        try:
            await self._site.start()
            logger.info(f"SseServerHandler started for agents {list(self._agents.keys())}. Listening on http://{host}:{port}")
        except OSError as e:
            logger.error(f"Failed to start SseServerHandler on http://{host}:{port}: {e}", exc_info=True)
            await self.stop_server()
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting SseServerHandler: {e}", exc_info=True)
            await self.stop_server()
            raise

    async def stop_server(self) -> None:
        logger.info(f"SseServerHandler for agents {list(self._agents.keys())} stopping...")
        
        for task in list(self._active_sse_forwarding_tasks.values()): # Iterate copy
            if task and not task.done():
                task.cancel()
        if self._active_sse_forwarding_tasks:
            await asyncio.gather(*self._active_sse_forwarding_tasks.values(), return_exceptions=True)
        self._active_sse_forwarding_tasks.clear()

        if self._site:
            try: await self._site.stop()
            except Exception as e: logger.error(f"Error stopping SseServerHandler TCPSite: {e}", exc_info=True)
            self._site = None
        
        if self._runner:
            try: await self._runner.cleanup()
            except Exception as e: logger.error(f"Error cleaning up SseServerHandler AppRunner: {e}", exc_info=True)
            self._runner = None
        
        logger.info(f"SseServerHandler for agents {list(self._agents.keys())} stopped.")

