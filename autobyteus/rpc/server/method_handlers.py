# file: autobyteus/autobyteus/rpc/server/method_handlers.py
import logging
from typing import Optional, Dict, Any, List, Callable, Awaitable, Tuple

from autobyteus.rpc.protocol import ProtocolMessage, MessageType, RequestType, ResponseType, ErrorCode
from autobyteus.rpc.server.base_method_handler import BaseMethodHandler
from autobyteus.agent.agent import Agent 
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.message.inter_agent_message import InterAgentMessage 


logger = logging.getLogger(__name__)

class DiscoverCapabilitiesHandler(BaseMethodHandler):
    """
    Handles the 'discover_capabilities' RPC method.
    Responds with the agent's ID, definition details, supported methods, and status,
    obtained via the Agent's public interface/context.
    """
    async def handle(self,
                     request_id: Optional[str],
                     params: Optional[Dict[str, Any]],
                     agent: Agent) -> ProtocolMessage: 
        logger.debug(f"DiscoverCapabilitiesHandler: Handling request_id '{request_id}' for agent '{agent.agent_id}'.")
        try:
            # Define capabilities, including the new stream download initiation method
            capabilities = {
                "post_user_message": {
                    "description": "Posts a message from an external user to the agent.",
                    "params": {"agent_input_user_message": "dict (serialized AgentInputUserMessage)"}
                },
                "post_inter_agent_message": {
                    "description": "Posts a message from another agent.",
                    "params": {"inter_agent_message": "dict (serialized InterAgentMessage)"}
                },
                "post_tool_execution_approval": {
                    "description": "Provides approval or denial for a pending tool execution.",
                    "params": {"tool_invocation_id": "str", "is_approved": "bool", "reason": "Optional[str]"}
                },
                "get_status": {
                    "description": "Gets the current operational status of the agent.",
                    "params": None 
                },
                # No specific invoke method for REQUEST_STREAM_DOWNLOAD, it's a top-level RequestType handled by its own handler.
                # However, if it were invoked via InvokeMethod, it would be listed here.
                # For clarity, methods invokable via InvokeMethodHandler are listed.
                # REQUEST_STREAM_DOWNLOAD will be handled by InitiateStreamDownloadHandler directly.
            }
            
            if not agent.context: 
                 logger.error(f"Agent '{agent.agent_id}' context is None. Cannot discover capabilities.")
                 return ProtocolMessage.create_error_response(
                    id=request_id,
                    code=ErrorCode.SERVER_ERROR_CAPABILITY_DISCOVERY_FAILED,
                    message="Agent context not available."
                 )

            # Explicitly list RequestTypes that this server (potentially) handles
            # This part of discover_capabilities might need to be more dynamic or list top-level RPC methods
            # rather than just methods invokable via InvokeMethodHandler.
            # For now, assume InvokeMethodHandler is the primary way to call agent functions.
            # The fact that REQUEST_STREAM_DOWNLOAD exists is a server capability.
            supported_rpc_request_types = [rt.value for rt in RequestType]


            result_data = {
                "agent_id": agent.agent_id, 
                "agent_name": agent.context.definition.name,
                "agent_role": agent.context.definition.role,
                "agent_description": agent.context.definition.description,
                "supported_rpc_request_types": supported_rpc_request_types, # Top-level RPC methods
                "invokable_methods_details": capabilities, # Methods callable via 'invoke_method'
                "status": agent.get_status().value, 
                "system_prompt_summary": agent.context.definition.system_prompt[:200] + "..." if len(agent.context.definition.system_prompt) > 200 else agent.context.definition.system_prompt,
                "tool_names": agent.context.definition.tool_names,
            }
            return ProtocolMessage.create_response(
                id=request_id,
                result=result_data,
                response_type=ResponseType.CAPABILITIES_RESPONSE
            )
        except Exception as e:
            logger.error(f"Error in DiscoverCapabilitiesHandler for agent '{agent.agent_id}': {e}", exc_info=True)
            return ProtocolMessage.create_error_response(
                id=request_id,
                code=ErrorCode.SERVER_ERROR_CAPABILITY_DISCOVERY_FAILED,
                message=f"Failed to discover capabilities: {e}"
            )


class InvokeMethodHandler(BaseMethodHandler):
    """
    Handles the 'invoke_method' RPC method.
    It dispatches to public methods of the Agent instance based on 'method_name'.
    """

    def __init__(self):
        # Map method names to Agent's public API methods (or wrappers around them)
        self._method_map: Dict[str, Callable[[Optional[str], Dict[str, Any], Agent], Awaitable[ProtocolMessage]]] = {
            "post_user_message": self._handle_post_user_message,
            "post_inter_agent_message": self._handle_post_inter_agent_message,
            "post_tool_execution_approval": self._handle_post_tool_execution_approval,
            "get_status": self._handle_get_status,
        }

    async def handle(self,
                     request_id: Optional[str],
                     params: Optional[Dict[str, Any]],
                     agent: Agent) -> ProtocolMessage: 
        if not params or "method_name" not in params:
            return ProtocolMessage.create_error_response(
                id=request_id,
                code=ErrorCode.INVALID_PARAMS,
                message="'method_name' is required in params for invoke_method."
            )

        method_name = params["method_name"]
        method_params = params.get("method_params", {})

        logger.debug(f"InvokeMethodHandler: Handling method '{method_name}' for agent '{agent.agent_id}' with request_id '{request_id}'.")

        handler_func = self._method_map.get(method_name)
        if not handler_func:
            return ProtocolMessage.create_error_response(
                id=request_id,
                code=ErrorCode.METHOD_NOT_FOUND,
                message=f"Method '{method_name}' is not supported by this agent server for invocation via InvokeMethodHandler."
            )

        try:
            return await handler_func(request_id, method_params, agent)
        except Exception as e:
            logger.error(f"Error invoking method '{method_name}' on agent '{agent.agent_id}': {e}", exc_info=True)
            return ProtocolMessage.create_error_response(
                id=request_id,
                code=ErrorCode.SERVER_ERROR_AGENT_PROCESSING_FAILED,
                message=f"Error processing method '{method_name}': {e}"
            )

    async def _handle_post_user_message(self, request_id: Optional[str], params: Dict[str, Any], agent: Agent) -> ProtocolMessage:
        serialized_msg = params.get("agent_input_user_message")
        if not isinstance(serialized_msg, dict):
            return ProtocolMessage.create_error_response(request_id, ErrorCode.INVALID_PARAMS, "'agent_input_user_message' (dict) parameter is required.")
        
        try:
            user_message = AgentInputUserMessage.from_dict(serialized_msg)
        except (ValueError, TypeError) as e:
            return ProtocolMessage.create_error_response(request_id, ErrorCode.INVALID_PARAMS, f"Invalid 'agent_input_user_message' structure: {e}")

        await agent.post_user_message(user_message) 
        logger.info(f"Agent '{agent.agent_id}' (via RPC): Called agent.post_user_message().")
        return ProtocolMessage.create_response(request_id, {"status": "User message posted to agent"}, ResponseType.ACKNOWLEDGEMENT)

    async def _handle_post_inter_agent_message(self, request_id: Optional[str], params: Dict[str, Any], agent: Agent) -> ProtocolMessage:
        serialized_msg = params.get("inter_agent_message")
        if not isinstance(serialized_msg, dict):
            return ProtocolMessage.create_error_response(request_id, ErrorCode.INVALID_PARAMS, "'inter_agent_message' (dict) parameter is required.")

        try:
            msg_type_str = serialized_msg.get("message_type")
            if not msg_type_str: raise ValueError("message_type missing")
            
            inter_agent_msg = InterAgentMessage.create_with_dynamic_message_type(
                recipient_role_name=serialized_msg.get("recipient_role_name"),
                recipient_agent_id=serialized_msg.get("recipient_agent_id"),
                content=serialized_msg.get("content"),
                message_type=msg_type_str,
                sender_agent_id=serialized_msg.get("sender_agent_id")
            )
        except (ValueError, TypeError) as e:
            return ProtocolMessage.create_error_response(request_id, ErrorCode.INVALID_PARAMS, f"Invalid 'inter_agent_message' structure: {e}")

        await agent.post_inter_agent_message(inter_agent_msg) 
        logger.info(f"Agent '{agent.agent_id}' (via RPC): Called agent.post_inter_agent_message() from '{inter_agent_msg.sender_agent_id}'.")
        return ProtocolMessage.create_response(request_id, {"status": "Inter-agent message posted to agent"}, ResponseType.ACKNOWLEDGEMENT)

    async def _handle_post_tool_execution_approval(self, request_id: Optional[str], params: Dict[str, Any], agent: Agent) -> ProtocolMessage:
        tool_invocation_id = params.get("tool_invocation_id")
        is_approved = params.get("is_approved")
        reason = params.get("reason")

        if not isinstance(tool_invocation_id, str) or not tool_invocation_id:
            return ProtocolMessage.create_error_response(request_id, ErrorCode.INVALID_PARAMS, "'tool_invocation_id' (str) is required.")
        if not isinstance(is_approved, bool):
            return ProtocolMessage.create_error_response(request_id, ErrorCode.INVALID_PARAMS, "'is_approved' (bool) is required.")
        if reason is not None and not isinstance(reason, str):
            return ProtocolMessage.create_error_response(request_id, ErrorCode.INVALID_PARAMS, "'reason' must be a string if provided.")

        await agent.post_tool_execution_approval(tool_invocation_id, is_approved, reason) 
        status_str = "approved" if is_approved else "denied"
        logger.info(f"Agent '{agent.agent_id}' (via RPC): Called agent.post_tool_execution_approval() for id '{tool_invocation_id}' ({status_str}).")
        return ProtocolMessage.create_response(request_id, {"status": f"Tool approval ({status_str}) posted to agent"}, ResponseType.ACKNOWLEDGEMENT)

    async def _handle_get_status(self, request_id: Optional[str], params: Dict[str, Any], agent: Agent) -> ProtocolMessage:
        status_value = agent.get_status().value 
        logger.debug(f"Agent '{agent.agent_id}' (via RPC): Current status is '{status_value}'.")
        return ProtocolMessage.create_response(request_id, {"status": status_value, "agent_id": agent.agent_id})


class InitiateStreamDownloadHandler(BaseMethodHandler):
    """
    Handles the 'request_stream_download' RPC method.
    Interacts with the agent to prepare a streamable resource and returns
    information required by the client to download it, including a stream_id.
    The SseServerHandler will augment this response with the full download URL.
    """
    async def handle(self,
                     request_id: Optional[str],
                     params: Optional[Dict[str, Any]],
                     agent: Agent) -> ProtocolMessage:
        logger.debug(f"InitiateStreamDownloadHandler: Handling request_id '{request_id}' for agent '{agent.agent_id}' with params: {params}.")
        if not params:
            return ProtocolMessage.create_error_response(
                id=request_id,
                code=ErrorCode.INVALID_PARAMS,
                message="Parameters are required for requesting a stream download (e.g., resource identifier)."
            )

        try:
            # Agent must implement `prepare_resource_for_streaming`
            # This method is conceptual; actual signature might vary.
            # It should return (stream_id: str, metadata: Dict[str, Any])
            # The agent becomes responsible for managing the lifecycle of this stream_id
            # and providing data when get_stream_data(stream_id) is called by SseServerHandler.
            if not hasattr(agent, "prepare_resource_for_streaming"):
                logger.error(f"Agent '{agent.agent_id}' does not support 'prepare_resource_for_streaming'.")
                return ProtocolMessage.create_error_response(
                    id=request_id,
                    code=ErrorCode.METHOD_NOT_FOUND,
                    message=f"Agent '{agent.agent_id}' cannot prepare streamable resources."
                )
            
            # Type hint for clarity if agent method is known
            # stream_id, metadata = await agent.prepare_resource_for_streaming(params)
            stream_preparation_result: Tuple[str, Dict[str, Any]] = await agent.prepare_resource_for_streaming(params)
            stream_id, metadata = stream_preparation_result
            
            logger.info(f"Agent '{agent.agent_id}' prepared stream_id '{stream_id}' for request_id '{request_id}'.")

            # The SseServerHandler will add the 'download_url' to this result later
            # agent_id_on_server is also added by SseServerHandler for constructing the URL
            result_payload = {
                "stream_id": stream_id,
                "metadata": metadata,
                # "agent_id_on_server": agent.agent_id # Or the server_key if different. SseServerHandler knows this.
            }
            
            return ProtocolMessage.create_response(
                id=request_id,
                result=result_payload,
                response_type=ResponseType.STREAM_DOWNLOAD_READY
            )
        except Exception as e:
            logger.error(f"Error in InitiateStreamDownloadHandler for agent '{agent.agent_id}': {e}", exc_info=True)
            return ProtocolMessage.create_error_response(
                id=request_id,
                code=ErrorCode.SERVER_ERROR_STREAM_PREPARATION_FAILED,
                message=f"Agent failed to prepare stream: {e}"
            )
