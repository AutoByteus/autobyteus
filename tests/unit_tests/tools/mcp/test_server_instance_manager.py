import pytest

from autobyteus.tools.mcp.server_instance_manager import McpServerInstanceManager
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.types import WebsocketMcpServerConfig
from autobyteus.tools.mcp.server import WebsocketManagedMcpServer


@pytest.fixture(autouse=True)
def clear_singletons():
    """Ensure each test runs with clean singleton instances."""
    for singleton in (McpServerInstanceManager, McpConfigService):
        if singleton in singleton._instances:
            del singleton._instances[singleton]
    yield


def test_get_server_instance_websocket_transport():
    manager = McpServerInstanceManager()
    config_service = McpConfigService()
    config_service.clear_configs()
    ws_config = WebsocketMcpServerConfig(
        server_id="ws_server",
        url="wss://localhost:8765/mcp",
    )
    config_service.add_config(ws_config)

    server_instance = manager.get_server_instance(agent_id="agent_a", server_id="ws_server")

    assert isinstance(server_instance, WebsocketManagedMcpServer)
