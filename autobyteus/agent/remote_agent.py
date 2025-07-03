# file: autobyteus/autobyteus/agent/remote_agent.py
import asyncio
import logging
import uuid # For generating default request IDs if ProtocolMessage doesn't
from typing import Optional, Dict, Any, AsyncIterator

from autobyteus.agent.agent import Agent 
from autobyteus.agent.phases import AgentOperationalPhase
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
        self._remote_status: AgentOperationalPhase = AgentOperationalPhase.UNINITIALIZED 

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
            initial_status_str = response_msg.result.get("status") # 'status' key for legacy, but should be 'phase'
            initial_phase_str = response_msg.result.get("phase", initial_status_str) # Prefer 'phase'
            if initial_phase_str:
                try: self._remote_status = AgentOperationalPhase(initial_phase_str)
                except ValueError: logger.warning(f"Invalid phase '{initial_phase_str}' from discovery."); self._remote_status = AgentOperationalPhase.UNINITIALIZED
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

    def get_current_phase(self) -> AgentOperationalPhase:
        if not self._is_initialized:
            logger.warning(f"RemoteAgentProxy '{self.agent_id}': get_current_phase called before initialization.")
        # Returns cached status updated by discovery or potentially by SSE events.
        return self._remote_status

    @property
    def is_running(self) -> bool:
        # A remote agent is "running" if it's not in a terminal state or uninitialized.
        if self._remote_status:
            return not self._remote_status.is_terminal() and self._remote_status != AgentOperationalPhase.UNINITIALIZED
        return False

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
        self._remote_status = AgentOperationalPhase.SHUTDOWN_COMPLETE 

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
        
        logger.info(f"RemoteAgentProxy '{self.agent_id}': Starting to stream events (Target: {self.target_agent_id_on_server or 'default'}).")
        async for event in self._connection.events():
            # Update remote status if a phase transition event is received
            if event.type == MessageType.EVENT and event.event_type == "agent_phase_transition" and event.payload:
                new_phase_str = event.payload.get("new_phase")
                if new_phase_str:
                    try: 
                        self._remote_status = AgentOperationalPhase(new_phase_str)
                        logger.debug(f"RemoteAgentProxy '{self.agent_id}': Remote phase updated to {self._remote_status.value}")
                    except ValueError: 
                        logger.warning(f"Received invalid phase '{new_phase_str}' via SSE event.")
            yield event


    def __repr__(self) -> str:
        conn_status = self._connection.is_connected if self._connection else False
        return (f"<RemoteAgentProxy effective_id='{self.agent_id}' "
                f"(DiscoveredRemoteID: {self._remote_agent_id_from_discovery or 'N/A'}) "
                f"server_cfg='{self.server_config_id}' target_on_server='{self.target_agent_id_on_server or 'N/A'}' connected={conn_status}>")
