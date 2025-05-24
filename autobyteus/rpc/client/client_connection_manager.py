# file: autobyteus/autobyteus/rpc/client/client_connection_manager.py
import logging
from typing import Dict, Optional

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.rpc.config import AgentServerConfig, AgentServerRegistry, default_agent_server_registry
from autobyteus.rpc.transport_type import TransportType
from .abstract_client_connection import AbstractClientConnection
from .stdio_client_connection import StdioClientConnection
from .sse_client_connection import SseClientConnection # Import SseClientConnection

logger = logging.getLogger(__name__)

class ClientConnectionManager(metaclass=SingletonMeta):
    """
    Manages the creation and caching of AbstractClientConnection instances.
    Uses AgentServerRegistry to find server configurations.
    """

    def __init__(self, agent_server_registry: AgentServerRegistry = default_agent_server_registry):
        self._agent_server_registry: AgentServerRegistry = agent_server_registry
        self._active_connections: Dict[str, AbstractClientConnection] = {} # Cache connections by server_id
        logger.info("ClientConnectionManager initialized.")

    async def get_connection(self, server_config_id: str) -> AbstractClientConnection:
        """
        Gets or creates a client connection for the given server configuration ID.
        If a connection for this ID already exists and is connected, it's returned.
        Otherwise, a new connection is established.

        Args:
            server_config_id: The ID of the AgentServerConfig to connect to.

        Returns:
            An AbstractClientConnection instance.

        Raises:
            ValueError: If server_config_id is not found or config is invalid.
            ConnectionError: If establishing a new connection fails.
        """
        if server_config_id in self._active_connections:
            conn = self._active_connections[server_config_id]
            if conn.is_connected: 
                logger.debug(f"Returning cached and connected connection for '{server_config_id}'.")
                return conn
            else:
                logger.info(f"Cached connection for '{server_config_id}' found but not connected. Attempting to recreate.")
                await self.close_connection(server_config_id)


        server_config: Optional[AgentServerConfig] = self._agent_server_registry.get_config(server_config_id)
        if not server_config:
            raise ValueError(f"AgentServerConfig not found in registry for server_id: '{server_config_id}'.")

        connection: AbstractClientConnection
        if server_config.transport_type == TransportType.STDIO:
            connection = StdioClientConnection(server_config)
        elif server_config.transport_type == TransportType.SSE:
            connection = SseClientConnection(server_config) # Added SSE case
        else:
            raise NotImplementedError(f"Unsupported transport type '{server_config.transport_type}' for server_id '{server_config_id}'.")

        try:
            await connection.connect()
            self._active_connections[server_config_id] = connection
            logger.info(f"Successfully established new connection for server_id '{server_config_id}' type '{server_config.transport_type}'.")
            return connection
        except Exception as e:
            logger.error(f"Failed to establish connection for server_id '{server_config_id}': {e}", exc_info=True)
            await connection.close() # Ensure cleanup on failed connect
            if server_config_id in self._active_connections:
                 del self._active_connections[server_config_id]
            raise ConnectionError(f"Failed to connect to server '{server_config_id}': {e}") from e


    async def close_connection(self, server_config_id: str) -> None:
        """
        Closes and removes a specific connection from the manager.

        Args:
            server_config_id: The ID of the server connection to close.
        """
        connection = self._active_connections.pop(server_config_id, None)
        if connection:
            logger.info(f"Closing connection for server_id '{server_config_id}'.")
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing connection for server_id '{server_config_id}': {e}", exc_info=True)
        else:
            logger.debug(f"No active connection found for server_id '{server_config_id}' to close.")

    async def close_all_connections(self) -> None:
        """Closes all active connections managed by this instance."""
        logger.info(f"Closing all {len(self._active_connections)} active connections.")
        for server_id in list(self._active_connections.keys()):
            await self.close_connection(server_id)
        logger.info("All active connections have been requested to close.")

default_client_connection_manager = ClientConnectionManager()

if __name__ == "__main__": # pragma: no cover
    logging.basicConfig(level=logging.DEBUG)
    
    # Mock server configs
    mock_stdio_id = "mock_stdio_ccm"
    mock_stdio_cfg = AgentServerConfig(
        server_id=mock_stdio_id,
        transport_type=TransportType.STDIO,
        stdio_command=["python", "-c", "import sys, time, json; print(json.dumps({'type':'response', 'id':'1', 'result':{'status':'ok'}}), flush=True); time.sleep(0.1); sys.exit(0)"]
    )
    default_agent_server_registry.register_config(mock_stdio_cfg)

    mock_sse_id = "mock_sse_ccm"
    mock_sse_cfg = AgentServerConfig(
        server_id=mock_sse_id,
        transport_type=TransportType.SSE,
        sse_base_url="http://localhost:12345", # Dummy URL, server won't actually run here
        sse_request_endpoint="/rpc",
        sse_events_endpoint="/stream"
    )
    default_agent_server_registry.register_config(mock_sse_cfg)


    manager = default_client_connection_manager

    async def main_ccm_test():
        stdio_conn = None
        sse_conn = None
        try:
            logger.info(f"Testing CCM with Stdio: {mock_stdio_id}")
            stdio_conn = await manager.get_connection(mock_stdio_id)
            logger.info(f"Stdio connection: {stdio_conn}")
            if stdio_conn.is_connected:
                # Test send_request on stdio_conn
                req = ProtocolMessage.create_request(method="test", id="1")
                resp = await stdio_conn.send_request(req)
                logger.info(f"Stdio test response: {resp}")


            logger.info(f"Testing CCM with SSE: {mock_sse_id}")
            sse_conn = await manager.get_connection(mock_sse_id) # This will create SseClientConnection and its session
            logger.info(f"SSE connection: {sse_conn}")
            # Actual SSE requests would fail here as no server is running at localhost:12345

        except Exception as e:
            logger.error(f"Error in CCM main_ccm_test: {e}", exc_info=True)
        finally:
            logger.info("Closing all connections via CCM.")
            await manager.close_all_connections()
            default_agent_server_registry.clear() # Clean up registry for other tests if any

    asyncio.run(main_ccm_test())
