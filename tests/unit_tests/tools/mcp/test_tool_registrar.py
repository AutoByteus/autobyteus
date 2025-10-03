# file: autobyteus/tests/unit_tests/tools/mcp/test_tool_registrar.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from autobyteus.tools.mcp.tool_registrar import McpToolRegistrar # Corrected import
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.types import StdioMcpServerConfig
from autobyteus.tools.mcp.server_instance_manager import McpServerInstanceManager
from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.utils.parameter_schema import ParameterType

# Mock the external mcp.types.Tool for type checking and isolation
# This is a class, so we mock its instances
MockMcpTool = MagicMock()
MockMcpTool.name = "remoteToolA"
MockMcpTool.description = "A remote tool for testing."
MockMcpTool.inputSchema = {"type": "object", "properties": {"paramA": {"type": "string"}}}

@pytest.fixture(autouse=True)
def clear_singleton_cache():
    """Ensures each test gets a fresh singleton instance."""
    singletons_to_clear = [McpToolRegistrar, McpConfigService, ToolRegistry, McpServerInstanceManager]
    for singleton_class in singletons_to_clear:
        if singleton_class in singleton_class._instances:
            del singleton_class._instances[singleton_class]
    yield

@pytest.fixture
def mock_dependencies(mocker):
    """Provides a fresh registrar instance with mocked dependencies for each test."""
    # Patch the dependencies at the location where they are imported by the registrar
    mocker.patch('autobyteus.tools.mcp.tool_registrar.McpConfigService')
    mocker.patch('autobyteus.tools.mcp.tool_registrar.ToolRegistry')
    mocker.patch('autobyteus.tools.mcp.tool_registrar.McpServerInstanceManager')
    
    # Now that the singletons are patched, instantiating the registrar will
    # cause it to be initialized with our mocks.
    registrar = McpToolRegistrar()
    
    return {
        "registrar": registrar,
        "config_service": registrar._config_service,
        "tool_registry": registrar._tool_registry,
        "instance_manager": registrar._instance_manager,
    }

@pytest.mark.asyncio
async def test_reload_all_mcp_tools(mock_dependencies, mocker):
    """Tests the full refresh capability of `reload_all_mcp_tools`."""
    registrar = mock_dependencies["registrar"]
    mock_config_service = mock_dependencies["config_service"]
    mock_tool_registry = mock_dependencies["tool_registry"]
    
    # --- Arrange ---
    server_config = StdioMcpServerConfig(server_id="server1", command="cmd1", enabled=True, tool_name_prefix="s1_")
    mock_config_service.get_all_configs.return_value = [server_config]
    
    # Directly patch the registrar's helper method to isolate its logic from connection details
    mock_fetch = mocker.patch.object(registrar, '_fetch_tools_from_server', new_callable=AsyncMock)
    mock_fetch.return_value = [MockMcpTool]

    # Prime the registrar with a stale server to test cleanup
    stale_tool_def = MagicMock(spec=ToolDefinition)
    stale_tool_def.name = "stale_tool"  # FIX: Correctly set the name attribute
    registrar._registered_tools_by_server["stale_server"] = [stale_tool_def]
    
    # --- Act ---
    await registrar.reload_all_mcp_tools()

    # --- Assert ---
    mock_config_service.get_all_configs.assert_called_once()
    mock_fetch.assert_awaited_once_with(server_config)
    
    # Assert that the stale tool was unregistered
    mock_tool_registry.unregister_tool.assert_called_once_with("stale_tool")
    
    # Assert that the new tool was registered
    mock_tool_registry.register_tool.assert_called_once()
    registered_def = mock_tool_registry.register_tool.call_args[0][0]
    assert isinstance(registered_def, ToolDefinition)
    assert registered_def.name == "s1_remoteToolA"
    assert registered_def.category == "server1" # Category is server_id
    assert registered_def.metadata["mcp_server_id"] == "server1"

    # Assert internal state is correct
    assert "stale_server" not in registrar._registered_tools_by_server
    assert "server1" in registrar._registered_tools_by_server
    assert len(registrar._registered_tools_by_server["server1"]) == 1

@pytest.mark.asyncio
async def test_register_server(mock_dependencies, mocker):
    """Tests registering a single server with a config object, ensuring old tools for that server are unregistered first."""
    registrar = mock_dependencies["registrar"]
    mock_tool_registry = mock_dependencies["tool_registry"]
    mock_config_service = mock_dependencies["config_service"]

    # --- Arrange ---
    target_config = StdioMcpServerConfig(server_id="target_server", command="cmd_target", enabled=True)
    
    mock_fetch = mocker.patch.object(registrar, '_fetch_tools_from_server', new_callable=AsyncMock)
    mock_fetch.return_value = [MockMcpTool]

    # Prime the registrar with a stale tool for the *same* server
    stale_tool_def = MagicMock(spec=ToolDefinition)
    stale_tool_def.name = "old_tool_for_target"  # FIX: Correctly set the name attribute
    registrar._registered_tools_by_server["target_server"] = [stale_tool_def]
    
    # --- Act ---
    await registrar.register_server(config_object=target_config)

    # --- Assert ---
    mock_fetch.assert_awaited_once_with(target_config)
    mock_tool_registry.unregister_tool.assert_called_once_with("old_tool_for_target")
    mock_tool_registry.register_tool.assert_called_once()
    mock_config_service.add_config.assert_called_once_with(target_config)

@pytest.mark.asyncio
async def test_load_and_register_server(mock_dependencies, mocker):
    """Tests the convenience method for loading a server from a dictionary."""
    registrar = mock_dependencies["registrar"]
    mock_config_service = mock_dependencies["config_service"]
    
    # --- Arrange ---
    target_config_dict = {"target_server": {"transport_type": "stdio", "command": "cmd_target"}}
    # Mock the config service to return a valid object when it's called
    validated_config = StdioMcpServerConfig(server_id="target_server", command="cmd_target")
    mock_config_service.load_config_from_dict.return_value = validated_config

    # Mock the actual registration method that will be called internally
    mock_register_server = mocker.patch.object(registrar, 'register_server', new_callable=AsyncMock)

    # --- Act ---
    await registrar.load_and_register_server(config_dict=target_config_dict)

    # --- Assert ---
    # Assert that the dictionary was passed to the config loader
    mock_config_service.load_config_from_dict.assert_called_once_with(target_config_dict)
    # Assert that the main registration method was then called with the validated object
    mock_register_server.assert_awaited_once_with(validated_config)


@pytest.mark.asyncio
async def test_reload_all_mcp_tools_fetch_fails(mock_dependencies, mocker):
    """Tests that a failure during tool fetching is handled gracefully during a full reload."""
    registrar = mock_dependencies["registrar"]
    mock_config_service = mock_dependencies["config_service"]
    mock_tool_registry = mock_dependencies["tool_registry"]

    # --- Arrange ---
    server_config = StdioMcpServerConfig(server_id="server_err", command="cmd", enabled=True)
    mock_config_service.get_all_configs.return_value = [server_config]
    
    mock_fetch = mocker.patch.object(registrar, '_fetch_tools_from_server', new_callable=AsyncMock)
    mock_fetch.side_effect = RuntimeError("Discovery network failed")

    # --- Act ---
    await registrar.reload_all_mcp_tools()

    # --- Assert ---
    mock_fetch.assert_awaited_once_with(server_config)
    mock_tool_registry.register_tool.assert_not_called()
    assert "server_err" not in registrar._registered_tools_by_server

@pytest.mark.asyncio
async def test_list_remote_tools_previews_without_side_effects(mock_dependencies, mocker):
    """Tests that `list_remote_tools` discovers but does not register."""
    registrar = mock_dependencies["registrar"]
    mock_tool_registry = mock_dependencies["tool_registry"]

    # --- Arrange ---
    preview_config = StdioMcpServerConfig(server_id="preview_server", command="preview_cmd")
    
    mock_fetch = mocker.patch.object(registrar, '_fetch_tools_from_server', new_callable=AsyncMock)
    mock_fetch.return_value = [MockMcpTool]

    # --- Act ---
    tool_defs = await registrar.list_remote_tools(mcp_config=preview_config)

    # --- Assert ---
    mock_fetch.assert_awaited_once_with(preview_config)
    
    assert len(tool_defs) == 1
    assert isinstance(tool_defs[0], ToolDefinition)
    assert tool_defs[0].name == "remoteToolA"
    assert tool_defs[0].metadata["mcp_server_id"] == "preview_server"
    
    mock_tool_registry.register_tool.assert_not_called()
    assert not registrar._registered_tools_by_server

def test_unregister_tools_from_server(mock_dependencies):
    """Tests the unregister_tools_from_server method's logic."""
    registrar = mock_dependencies["registrar"]
    mock_tool_registry = mock_dependencies["tool_registry"]

    tool_def = MagicMock(spec=ToolDefinition); tool_def.name = "tool_to_remove"
    registrar._registered_tools_by_server["server1"] = [tool_def]

    result = registrar.unregister_tools_from_server("server1")

    assert result is True
    mock_tool_registry.unregister_tool.assert_called_once_with("tool_to_remove")
    assert "server1" not in registrar._registered_tools_by_server
