# file: autobyteus/autobyteus/agent/remote_agent.py
import asyncio
import logging
import uuid # For generating default request IDs if ProtocolMessage doesn't
from typing import Optional, Dict, Any, AsyncIterator

from autobyteus.agent.agent import Agent 
from autobyteus.agent.status import AgentStatus
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.rpc.client import default_client_connection_manager, AbstractClientConnection
from autobyteus.rpc.protocol import ProtocolMessage, MessageType, RequestType, ResponseType, ErrorCode
from autobyteus.rpc.config import AgentServerConfig, default_agent_server_registry
from autobyteus.rpc.transport_type import TransportType # For type checking config


logger = logging.getLogger(__name__)

class RemoteAgentProxy(Agent):
    """
    Provides an Agent-like interface for interacting with a remote Agent Server.
    It handles RPC communication and capability discovery.
    Can target a specific agent on a multi-agent gateway server if target_agent_id_on_server is provided.
    """
    def __init__(self, 
                 server_config_id: str, 
                 target_agent_id_on_server: Optional[str] = None, # Added for multi-agent servers
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Initializes the RemoteAgentProxy.

        Args:
            server_config_id: The ID of the AgentServerConfig in the AgentServerRegistry
                              that specifies how to connect to the remote agent server/gateway.
            target_agent_id_on_server: Optional. If the server_config_id points to a multi-agent
                                       gateway, this specifies the ID of the target agent on that
                                       server. This ID is used for routing by the server.
            loop: The asyncio event loop. If None, the running loop is used.
        """
        self.server_config_id: str = server_config_id
        self.target_agent_id_on_server: Optional[str] = target_agent_id_on_server
        
        self._client_connection_manager = default_client_connection_manager
        self._connection: Optional[AbstractClientConnection] = None
        self._server_config: Optional[AgentServerConfig] = None # Will store the resolved config
        self._loop = loop or asyncio.get_running_loop()

        self._remote_agent_id_from_discovery: Optional[str] = None 
        self._remote_capabilities: Dict[str, Any] = {} 
        self._remote_status: AgentStatus = AgentStatus.NOT_STARTED 

        # For Agent compatibility:
        # If target_agent_id_on_server is known, use it for a more descriptive initial proxy agent_id.
        # This will be overwritten by the actual agent_id from discovery.
        default_proxy_id_suffix = target_agent_id_on_server or server_config_id
        self.agent_id: str = f"remote_proxy_for_{default_proxy_id_suffix}"
        self.context = None 
                            
        self._is_initialized: bool = False
        self._initialization_lock = asyncio.Lock()

        logger.info(f"RemoteAgentProxy for server_id '{server_config_id}' (Targeting: {target_agent_id_on_server or 'N/A'}) created. Not yet initialized.")

    async def _ensure_initialized(self):
        async with self._initialization_lock:
            if self._is_initialized:
                return
            
            if not self._connection or not self._connection.is_connected:
                logger.info(f"RemoteAgentProxy '{self.agent_id}': Attempting connection to server_config_id '{self.server_config_id}'.")
                # Resolve server_config here as it's needed for SSE event URL construction too
                self._server_config = default_agent_server_registry.get_config(self.server_config_id)
                if not self._server_config:
                    raise ValueError(f"AgentServerConfig not found for ID '{self.server_config_id}'.")
                self._connection = await self._client_connection_manager.get_connection(self.server_config_id)
            
            await self._discover_capabilities() # This will use self.target_agent_id_on_server
            self._is_initialized = True
            logger.info(f"RemoteAgentProxy '{self.agent_id}' initialized. Discovered Remote Agent ID: '{self._remote_agent_id_from_discovery}'.")


    async def _discover_capabilities(self):
        if not self._connection:
            raise ConnectionError("Cannot discover capabilities: not connected.")

        params_for_discovery: Dict[str, Any] = {}
        if self.target_agent_id_on_server:
            params_for_discovery["target_agent_id"] = self.target_agent_id_on_server
        
        request_msg = ProtocolMessage.create_request(
            method=RequestType.DISCOVER_CAPABILITIES,
            params=params_for_discovery if params_for_discovery else None
        )
        logger.debug(f"RemoteAgentProxy '{self.agent_id}': Sending discover_capabilities request with params: {params_for_discovery}.")
        
        response_msg = await self._connection.send_request(request_msg)

        if response_msg.type == MessageType.RESPONSE and response_msg.result:
            self._remote_agent_id_from_discovery = response_msg.result.get("agent_id")
            # Update proxy's agent_id to the actual discovered ID for better logging/identification
            if self._remote_agent_id_from_discovery:
                self.agent_id = self._remote_agent_id_from_discovery 
            
            self._remote_capabilities = response_msg.result.get("capabilities_details", {}) # Use detailed map
            initial_status_str = response_msg.result.get("status")
            if initial_status_str:
                try: self._remote_status = AgentStatus(initial_status_str)
                except ValueError: logger.warning(f"Invalid status '{initial_status_str}' from discovery."); self._remote_status = AgentStatus.NOT_STARTED
            logger.info(f"RemoteAgentProxy (now ID: '{self.agent_id}'): Capabilities discovered. Remote Caps: {list(self._remote_capabilities.keys())}")
        elif response_msg.type == MessageType.ERROR and response_msg.error:
            err = response_msg.error
            logger.error(f"RemoteAgentProxy '{self.agent_id}': Error discovering capabilities: {err.code} - {err.message}")
            raise RuntimeError(f"Failed to discover remote agent capabilities: {err.message}")
        else:
            logger.error(f"RemoteAgentProxy '{self.agent_id}': Unexpected response during capability discovery: {response_msg.to_json_str()}")
            raise RuntimeError("Unexpected response from remote agent during capability discovery.")

    async def _invoke_remote_method(self, method_name: str, method_params: Optional[Dict[str, Any]] = None) -> Any:
        await self._ensure_initialized()
        if not self._connection: 
            raise ConnectionError("Not connected to remote agent.")

        # Construct parameters for the INVOKE_METHOD RPC call itself
        rpc_params: Dict[str, Any] = {
            "method_name": method_name,
            "method_params": method_params or {}
        }
        if self.target_agent_id_on_server:
            rpc_params["target_agent_id"] = self.target_agent_id_on_server
        
        request_msg = ProtocolMessage.create_request(
            method=RequestType.INVOKE_METHOD,
            params=rpc_params
        )
        log_method_params = str(method_params)[:100] + "..." if method_params and len(str(method_params)) > 100 else method_params
        logger.debug(f"RemoteAgentProxy '{self.agent_id}': Invoking remote method '{method_name}' (Targeting: {self.target_agent_id_on_server or 'default'}) with params: {log_method_params}")
        
        response_msg = await self._connection.send_request(request_msg)

        if response_msg.type == MessageType.RESPONSE:
            logger.debug(f"RemoteAgentProxy '{self.agent_id}': Received successful response for '{method_name}'.")
            return response_msg.result 
        elif response_msg.type == MessageType.ERROR and response_msg.error:
            err = response_msg.error
            logger.error(f"RemoteAgentProxy '{self.agent_id}': Error invoking remote method '{method_name}': {err.code} - {err.message}")
            raise RuntimeError(f"Error from remote agent on method '{method_name}': {err.message}")
        else:
            logger.error(f"RemoteAgentProxy '{self.agent_id}': Unexpected response invoking method '{method_name}': {response_msg.to_json_str()}")
            raise RuntimeError(f"Unexpected response from remote agent invoking '{method_name}'.")

    async def post_user_message(self, agent_input_user_message: AgentInputUserMessage) -> None:
        params = {"agent_input_user_message": agent_input_user_message.to_dict()}
        await self._invoke_remote_method("post_user_message", params)
        logger.debug(f"RemoteAgentProxy '{self.agent_id}': post_user_message request sent.")

    async def post_inter_agent_message(self, inter_agent_message: InterAgentMessage) -> None:
        params = { "inter_agent_message": {
                "recipient_role_name": inter_agent_message.recipient_role_name,
                "recipient_agent_id": inter_agent_message.recipient_agent_id,
                "content": inter_agent_message.content,
                "message_type": str(inter_agent_message.message_type.value), 
                "sender_agent_id": inter_agent_message.sender_agent_id,
            }
        }
        await self._invoke_remote_method("post_inter_agent_message", params)
        logger.debug(f"RemoteAgentProxy '{self.agent_id}': post_inter_agent_message request sent.")
        
    async def post_tool_execution_approval(self,
                                         tool_invocation_id: str,
                                         is_approved: bool,
                                         reason: Optional[str] = None) -> None:
        params = { "tool_invocation_id": tool_invocation_id, "is_approved": is_approved, "reason": reason}
        await self._invoke_remote_method("post_tool_execution_approval", params)
        logger.debug(f"RemoteAgentProxy '{self.agent_id}': post_tool_execution_approval sent.")

    def get_status(self) -> AgentStatus:
        if not self._is_initialized:
            logger.warning(f"RemoteAgentProxy '{self.agent_id}': get_status called before initialization.")
        # Consider making get_status async and actually calling remote if needed for "live" status
        # For now, returns cached status updated by discovery or potentially by SSE events later.
        return self._remote_status

    @property
    def is_running(self) -> bool:
        running_states = [AgentStatus.STARTING, AgentStatus.RUNNING, AgentStatus.IDLE, AgentStatus.WAITING_FOR_RESPONSE]
        return self._remote_status in running_states

    def start(self) -> None:
        # For RemoteAgentProxy, start() implies ensuring connection and readiness.
        # The actual remote agent lifecycle is independent.
        if not self._is_initialized:
            logger.info(f"RemoteAgentProxy '{self.agent_id}': start() called. Ensuring initialization (async).")
            if self._loop.is_running(): asyncio.create_task(self._ensure_initialized())
            else:
                try: self._loop.run_until_complete(self._ensure_initialized())
                except RuntimeError as e: 
                     if "cannot be nested" in str(e): logger.warning("RemoteAgentProxy.start() in sync context with running loop.")
                     else: raise

    async def stop(self, timeout: float = 10.0) -> None:
        logger.info(f"RemoteAgentProxy '{self.agent_id}': stop() called. Closing connection to '{self.server_config_id}'.")
        if self._connection:
            await self._connection.close()
            self._connection = None
        self._is_initialized = False
        self._remote_status = AgentStatus.ENDED 

    def get_event_queues(self): 
        logger.warning("RemoteAgentProxy does not provide direct access to remote event queues.")
        return None

    async def stream_events(self) -> AsyncIterator[ProtocolMessage]:
        """
        Streams server-pushed events if connected via SSE.
        """
        await self._ensure_initialized() # Ensures self._connection and self._server_config are set
        if not self._connection:
            raise ConnectionError("Not connected to remote agent.")
        if not self._server_config or self._server_config.transport_type != TransportType.SSE:
            logger.warning(f"Event streaming only supported for SSE transport. Current: {self._server_config.transport_type if self._server_config else 'Unknown'}")
            if False: yield # Make it an async generator
            return

        # Modify SseClientConnection.events() to take target_agent_id_on_server if necessary,
        # or SseClientConnection itself constructs the correct events URL using this info.
        # Assuming SseClientConnection.events() is smart enough or configured for the target.
        # For now, SseClientConnection's __init__ takes the full AgentServerConfig,
        # and its events() method forms the URL. If target_agent_id_on_server is needed for
        # the event URL, SseClientConnection needs access to it or it needs to be part of AgentServerConfig.
        # Let's assume SseClientConnection's existing events() method is sufficient for now.
        # The events URL for SseClientConnection must be formed correctly by using
        # server_config.get_sse_full_events_url() and potentially appending self.target_agent_id_on_server.
        # This logic is better placed within SseClientConnection itself.
        # For now, let's assume self._connection.events() is correctly set up.
        
        logger.info(f"RemoteAgentProxy '{self.agent_id}': Starting to stream events (Target: {self.target_agent_id_on_server or 'default'}).")
        async for event in self._connection.events():
            # Potentially update self._remote_status if status update events are received
            if event.type == MessageType.EVENT and event.event_type == "agent_status_update" and event.payload:
                new_status_str = event.payload.get("status")
                if new_status_str:
                    try: self._remote_status = AgentStatus(new_status_str)
                    except ValueError: logger.warning(f"Received invalid status '{new_status_str}' via SSE event.")
            yield event


    def __repr__(self) -> str:
        conn_status = self._connection.is_connected if self._connection else False
        return (f"<RemoteAgentProxy effective_id='{self.agent_id}' "
                f"(DiscoveredRemoteID: {self._remote_agent_id_from_discovery or 'N/A'}) "
                f"server_cfg='{self.server_config_id}' target_on_server='{self.target_agent_id_on_server or 'N/A'}' connected={conn_status}>")

# Example usage would now involve setting up a multi-agent server using serve_multiple_agents_http_sse
# and then a RemoteAgentProxy connecting to it, specifying a target_agent_id_on_server.
