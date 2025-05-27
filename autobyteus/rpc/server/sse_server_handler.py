    # file: autobyteus/autobyteus/rpc/server/sse_server_handler.py
    import asyncio
    import logging
    import json
    from typing import Dict, Optional, Union, Set, cast, AsyncIterator 
    from weakref import WeakSet
    
    from aiohttp import web 
    from aiohttp_sse import sse_response 
    
    from autobyteus.agent.agent import Agent
    # MODIFIED: Import AgentEventStream (remains the same, but it's now the sole class)
    from autobyteus.agent.streaming import AgentEventStream 
    from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType 
    from autobyteus.rpc.protocol import ProtocolMessage, MessageType, ErrorCode, RequestType, ResponseType, EventType as RPCEventType 
    from autobyteus.rpc.server.base_method_handler import BaseMethodHandler
    from autobyteus.rpc.config import AgentServerConfig 
    
    logger = logging.getLogger(__name__)
    
    DEFAULT_STREAM_CHUNK_SIZE = 8192 
    
    class SseServerHandler:
        def __init__(self, agents: Dict[str, Agent], method_handlers: Dict[Union[RequestType, str], BaseMethodHandler]):
            self._agents: Dict[str, Agent] = agents
            self._method_handlers = method_handlers
            self._app = web.Application()
            self._runner: Optional[web.AppRunner] = None
            self._site: Optional[web.TCPSite] = None
            self._active_sse_forwarding_tasks: Dict[web.StreamResponse, asyncio.Task] = {}
            logger.info(f"SseServerHandler initialized to serve agents: {list(self._agents.keys())}.")
    
        def _setup_routes(self, config: AgentServerConfig):
            # ... (method body remains the same) ...
            rpc_request_path = config.sse_request_endpoint
            base_events_path = config.sse_events_endpoint.rstrip('/')
            full_events_path = f"{base_events_path}/{{agent_id_on_server}}"
            stream_download_prefix = config.sse_stream_download_path_prefix.rstrip('/')
            full_stream_download_path = f"{stream_download_prefix}/{{agent_id_on_server}}/{{stream_id}}"
            self._app.router.add_post(rpc_request_path, self.handle_rpc_request)
            self._app.router.add_get(full_events_path, self.handle_sse_events_subscription)
            self._app.router.add_get(full_stream_download_path, self.handle_http_stream_download)
            logger.info(f"SseServerHandler routes: POST {rpc_request_path} (RPC), GET {full_events_path} (SSE per agent), GET {full_stream_download_path} (HTTP Stream Download).")

        async def handle_rpc_request(self, http_request: web.Request) -> web.Response:
            # ... (method body remains the same) ...
            request_id: Optional[str] = None; raw_body_str: str = ""; target_agent_id: Optional[str] = None
            try:
                raw_body = await http_request.read(); raw_body_str = raw_body.decode()
                try: parsed_json_early = json.loads(raw_body_str); request_id = parsed_json_early.get("id")
                except json.JSONDecodeError: pass
                request_message = ProtocolMessage.from_json_str(raw_body_str); request_id = request_message.id 
                if request_message.type != MessageType.REQUEST or not request_message.method:
                    return self._create_json_error_response(request_id, ErrorCode.INVALID_REQUEST, "Must be REQUEST with method.", 400)
                if request_message.params and "target_agent_id" in request_message.params:
                    target_agent_id = str(request_message.params["target_agent_id"])
                if not target_agent_id: return self._create_json_error_response(request_id, ErrorCode.INVALID_PARAMS, "'target_agent_id' missing in request params.", 400)
                target_agent = self._agents.get(target_agent_id)
                if not target_agent: return self._create_json_error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"Agent with id '{target_agent_id}' not found.", 404)
                actual_handler_params = request_message.params
                handler = self._method_handlers.get(request_message.method)
                if not handler: return self._create_json_error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"RPC Method '{request_message.method}' not found.", 404)
                logger.debug(f"SseServerHandler dispatching RPC '{request_message.method}' (ReqID: {request_id}) to '{handler.__class__.__name__}' for agent '{target_agent_id}'.")
                response_proto = await handler.handle(request_id, actual_handler_params, target_agent) 
                if response_proto.response_type == ResponseType.STREAM_DOWNLOAD_READY and response_proto.result and "stream_id" in response_proto.result and target_agent_id: 
                    server_config: AgentServerConfig = http_request.app['agent_server_config']
                    full_url_prefix = server_config.get_sse_full_stream_download_url_prefix_for_agent(target_agent_id)
                    if full_url_prefix:
                        stream_id = response_proto.result["stream_id"]; download_url = f"{full_url_prefix.rstrip('/')}/{stream_id}"
                        response_proto.result["download_url"] = download_url; logger.info(f"Constructed download URL for stream_id '{stream_id}': {download_url}")
                    else: logger.error(f"Could not construct download_url for stream_id '{response_proto.result['stream_id']}'.")
                http_status = 200
                if response_proto.type == MessageType.ERROR and response_proto.error:
                    if response_proto.error.code == ErrorCode.METHOD_NOT_FOUND.value: http_status = 404
                    elif response_proto.error.code in [ErrorCode.INVALID_REQUEST.value, ErrorCode.INVALID_PARAMS.value, ErrorCode.PARSE_ERROR.value]: http_status = 400
                    else: http_status = 500
                return web.json_response(response_proto.model_dump(exclude_none=True), status=http_status)
            except json.JSONDecodeError as e: logger.error(f"Sse JSONDecodeError: {e}. Body: '{raw_body_str[:200]}'"); return self._create_json_error_response(request_id, ErrorCode.PARSE_ERROR, f"JSON parse error: {e}", 400)
            except ValueError as e: logger.error(f"Sse Protocol validation error: {e}. Body: '{raw_body_str[:200]}'"); return self._create_json_error_response(request_id, ErrorCode.INVALID_REQUEST, f"Invalid request: {e}", 400)
            except Exception as e: logger.error(f"Sse unexpected error: {e}", exc_info=True); return self._create_json_error_response(request_id, ErrorCode.INTERNAL_ERROR, f"Server error: {e}", 500)

        def _create_json_error_response(self, req_id: Optional[str], code: ErrorCode, msg: str, http_status: int) -> web.Response:
            # ... (method body remains the same) ...
            err_proto = ProtocolMessage.create_error_response(req_id, code, msg)
            return web.json_response(err_proto.model_dump(exclude_none=True), status=http_status)
    
        async def handle_sse_events_subscription(self, http_request: web.Request) -> web.StreamResponse:
            # ... (method body remains the same, it instantiates AgentEventStream and calls all_events()) ...
            agent_id_on_server = http_request.match_info.get("agent_id_on_server")
            if not agent_id_on_server: raise web.HTTPBadRequest(text="'agent_id_on_server' path param required.")
            target_agent = self._agents.get(agent_id_on_server)
            if not target_agent: raise web.HTTPNotFound(text=f"Agent '{agent_id_on_server}' not found.")
            client_addr = http_request.remote
            logger.info(f"SSE client {client_addr} subscribing to events for agent '{target_agent.agent_id}' (server key: '{agent_id_on_server}').")
            sse_resp = web.StreamResponse(status=200, reason='OK', headers={'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})
            await sse_resp.prepare(http_request) 
            forwarding_task = asyncio.create_task(self._stream_agent_events_to_client(sse_resp, target_agent, agent_id_on_server), name=f"sse_fwd_{target_agent.agent_id}_{client_addr}")
            self._active_sse_forwarding_tasks[sse_resp] = forwarding_task
            try: await forwarding_task 
            except asyncio.CancelledError: logger.info(f"SSE task for agent '{target_agent.agent_id}' to {client_addr} cancelled.")
            except Exception as e: logger.error(f"Error in SSE streaming for agent '{target_agent.agent_id}' to {client_addr}: {e}", exc_info=True)
            finally: logger.info(f"SSE client {client_addr} for agent '{target_agent.agent_id}' disconnected."); self._active_sse_forwarding_tasks.pop(sse_resp, None)
            return sse_resp

        async def _stream_agent_events_to_client(self, sse_client_resp: web.StreamResponse, agent: Agent, agent_id_on_server: str):
            # Instantiates AgentEventStream
            event_stream_provider = AgentEventStream(agent)
            logger.debug(f"SseServerHandler: Streaming events from agent '{agent.agent_id}' (key: {agent_id_on_server}) via AgentEventStream.all_events().")
            try:
                # Calls .all_events() method
                async for agent_event_obj in event_stream_provider.all_events(): 
                    if sse_client_resp.closed: break
                    rpc_event_type: RPCEventType
                    if agent_event_obj.event_type == StreamEventType.ASSISTANT_CHUNK: rpc_event_type = RPCEventType.AGENT_OUTPUT_CHUNK
                    elif agent_event_obj.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE: rpc_event_type = RPCEventType.AGENT_FINAL_MESSAGE
                    elif agent_event_obj.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY: rpc_event_type = RPCEventType.TOOL_LOG_ENTRY
                    elif agent_event_obj.event_type == StreamEventType.AGENT_STATUS_CHANGE: rpc_event_type = RPCEventType.AGENT_STATUS_UPDATE
                    elif agent_event_obj.event_type == StreamEventType.ERROR_EVENT: rpc_event_type = RPCEventType.AGENT_STATUS_UPDATE; logger.error(f"Unified stream error for agent '{agent.agent_id}': {agent_event_obj.data}")
                    else: rpc_event_type = RPCEventType.AGENT_STATUS_UPDATE; logger.warning(f"Unhandled StreamEventType '{agent_event_obj.event_type}' from agent '{agent.agent_id}'.")
                    payload_data = {"agent_id_on_server": agent_id_on_server, **agent_event_obj.data}
                    protocol_event_msg = ProtocolMessage.create_event(event_type=rpc_event_type, payload=payload_data)
                    try:
                        sse_event_str = f"event: {str(protocol_event_msg.event_type.value)}\ndata: {protocol_event_msg.to_json_str()}\n\n"
                        await sse_client_resp.write(sse_event_str.encode('utf-8'))
                    except ConnectionResetError: logger.info(f"SSE client reset for agent '{agent.agent_id}'."); break
                    except Exception as send_e: logger.error(f"Error sending SSE event for agent '{agent.agent_id}': {send_e}"); break 
                if not sse_client_resp.closed: await sse_client_resp.write_eof()
            except asyncio.CancelledError: logger.info(f"Event streaming for agent '{agent.agent_id}' (key: {agent_id_on_server}) cancelled.")
            except Exception as e: logger.error(f"Error in event streaming for agent '{agent.agent_id}' (key: {agent_id_on_server}): {e}", exc_info=True)
            finally: logger.debug(f"Finished event streaming from agent '{agent.agent_id}' (key: {agent_id_on_server}).")

        async def handle_http_stream_download(self, http_request: web.Request) -> web.StreamResponse:
            # ... (method body remains the same) ...
            agent_id_on_server = http_request.match_info.get("agent_id_on_server"); stream_id = http_request.match_info.get("stream_id")
            if not agent_id_on_server or not stream_id: raise web.HTTPBadRequest(text="'agent_id_on_server' and 'stream_id' path params required.")
            target_agent = self._agents.get(agent_id_on_server)
            if not target_agent: raise web.HTTPNotFound(text=f"Agent '{agent_id_on_server}' not found.")
            logger.info(f"HTTP stream download for agent '{target_agent.agent_id}' (key: '{agent_id_on_server}'), stream_id '{stream_id}'.")
            if not hasattr(target_agent, "get_stream_data") or not hasattr(target_agent, "cleanup_stream_resource"):
                raise web.HTTPNotImplemented(text=f"Agent '{target_agent.agent_id}' does not support stream retrieval.")
            try:
                get_stream_data_method = getattr(target_agent, "get_stream_data")
                data_iterator: AsyncIterator[bytes] = await get_stream_data_method(stream_id)
                response = web.StreamResponse(status=200, reason="OK", headers={"Content-Type": "application/octet-stream"})
                await response.prepare(http_request)
                async for chunk in data_iterator:
                    if not isinstance(chunk, bytes): logger.error(f"Agent '{target_agent.agent_id}' stream '{stream_id}' yielded non-bytes: {type(chunk)}."); break 
                    await response.write(chunk); await asyncio.sleep(0) 
                await response.write_eof(); logger.info(f"Streamed data for agent '{target_agent.agent_id}', stream_id '{stream_id}'."); return response
            except FileNotFoundError: logger.warning(f"Stream '{stream_id}' not found for agent '{target_agent.agent_id}'."); raise web.HTTPNotFound(text=f"Stream resource '{stream_id}' not found.")
            except asyncio.CancelledError: logger.info(f"HTTP stream download for '{stream_id}' (agent '{target_agent.agent_id}') cancelled."); raise 
            except Exception as e: logger.error(f"Error during HTTP stream download for '{stream_id}' (agent '{target_agent.agent_id}'): {e}", exc_info=True); raise web.HTTPInternalServerError(text="Error serving stream data.")
            finally:
                try: cleanup_method = getattr(target_agent, "cleanup_stream_resource"); await cleanup_method(stream_id); logger.debug(f"Agent '{target_agent.agent_id}' cleaned up stream '{stream_id}'.")
                except Exception as cleanup_e: logger.error(f"Error cleaning up stream '{stream_id}': {cleanup_e}", exc_info=True)

        async def start_server(self, config: AgentServerConfig):
            # ... (method body remains the same) ...
            if not config.sse_base_url: raise ValueError("SSE base URL required.")
            self._app['agent_server_config'] = config; self._setup_routes(config)
            host = config.sse_base_url.host or "0.0.0.0"; port = config.sse_base_url.port or 80
            self._runner = web.AppRunner(self._app); await self._runner.setup()
            self._site = web.TCPSite(self._runner, host, port)
            try: await self._site.start(); logger.info(f"SseServerHandler started for agents {list(self._agents.keys())} on http://{host}:{port}")
            except OSError as e: logger.error(f"Failed to start SseServer on http://{host}:{port}: {e}", exc_info=True); await self.stop_server(); raise
            except Exception as e: logger.error(f"Unexpected error starting SseServer: {e}", exc_info=True); await self.stop_server(); raise

        async def stop_server(self):
            # ... (method body remains the same) ...
            logger.info(f"SseServerHandler for agents {list(self._agents.keys())} stopping...")
            for task in list(self._active_sse_forwarding_tasks.values()): 
                if task and not task.done(): task.cancel()
            if self._active_sse_forwarding_tasks: await asyncio.gather(*self._active_sse_forwarding_tasks.values(), return_exceptions=True)
            self._active_sse_forwarding_tasks.clear()
            if self._site: try: await self._site.stop()
                except Exception as e: logger.error(f"Error stopping TCPSite: {e}", exc_info=True)
                self._site = None
            if self._runner: try: await self._runner.cleanup()
                except Exception as e: logger.error(f"Error cleaning AppRunner: {e}", exc_info=True)
                self._runner = None
            logger.info(f"SseServerHandler for agents {list(self._agents.keys())} stopped.")
    