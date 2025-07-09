# file: autobyteus/tests/unit_tests/tools/mcp/test_registrar.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from autobyteus.tools.mcp.registrar import McpToolRegistrar
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.types import StdioMcpServerConfig, McpTransportType
from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

# Mock external mcp.types
MockMcpToolType = MagicMock()
MockMcpListToolsResult = MagicMock()

@pytest.fixture
def mock_dependencies():
    """A fixture to provide mocked dependencies for the registrar."""
    with patch('autobyteus.tools.mcp.registrar.McpConfigService') as MockConfigService, \
         patch('autobyteus.tools.mcp.registrar.ToolRegistry') as MockToolRegistry, \
         patch('autobyteus.tools.mcp.registrar.StdioMcpCallHandler') as MockStdioHandler:
        
        # Instantiate the registrar within the context of the patches
        # to ensure its internal dependencies are the mocks
        registrar = McpToolRegistrar()
        
        yield {
            "registrar": registrar,
            "config_service": MockConfigService.return_value,
            "tool_registry": MockToolRegistry.return_value,
            "stdio_handler": MockStdioHandler.return_value
        }

@pytest.fixture(autouse=True)
def clear_singleton_cache():
    """Fixture to automatically clear singleton caches before each test."""
    # This ensures that each test gets a fresh instance of the singleton
    if McpToolRegistrar in McpToolRegistrar._instances:
        del McpToolRegistrar._instances[McpToolRegistrar]
    if McpConfigService in McpConfigService._instances:
        del McpConfigService._instances[McpConfigService]
    if ToolRegistry in ToolRegistry._instances:
        del ToolRegistry._instances[ToolRegistry]
    yield
    # Clean up after test
    if McpToolRegistrar in McpToolRegistrar._instances: del McpToolRegistrar._instances[McpToolRegistrar]
    if McpConfigService in McpConfigService._instances: del McpConfigService._instances[McpConfigService]
    if ToolRegistry in ToolRegistry._instances: del ToolRegistry._instances[ToolRegistry]


@pytest.mark.asyncio
async def test_discover_and_register_tools_full_scan(mock_dependencies):
    """Tests the default behavior of scanning all configured servers."""
    registrar = mock_dependencies["registrar"]
    mock_config_instance = mock_dependencies["config_service"]
    mock_tool_registry_instance = mock_dependencies["tool_registry"]
    mock_handler_instance = mock_dependencies["stdio_handler"]

    # --- Setup ---
    # Define the server configuration for the test
    server_config1 = StdioMcpServerConfig(server_id="server1", command="cmd1", enabled=True, tool_name_prefix="s1_")
    mock_config_instance.get_all_configs.return_value = [server_config1]

    # Define the mock response from the remote tool server
    remote_tool1_meta = MockMcpToolType()
    remote_tool1_meta.name = "toolA"
    remote_tool1_meta.description = "Tool A description"
    remote_tool1_meta.inputSchema = {"type": "object", "properties": {"paramA": {"type": "string"}}}
    
    list_tools_result = MockMcpListToolsResult()
    list_tools_result.tools = [remote_tool1_meta]

    # Set the return value on the handler's mock method
    mock_handler_instance.handle_call.return_value = list_tools_result

    # Prime the registrar with a fake pre-existing tool to test cleanup
    preexisting_tool_def = MagicMock(spec=ToolDefinition)
    preexisting_tool_def.name = "stale_tool"
    registrar._registered_tools_by_server["stale_server"] = [preexisting_tool_def]

    # --- Act ---
    await registrar.discover_and_register_tools()

    # --- Assertions ---
    # Assert that unregister was called for the stale tool
    mock_tool_registry_instance.unregister_tool.assert_called_once_with("stale_tool")

    # Assert discovery and registration happened for the new tool
    mock_config_instance.get_all_configs.assert_called_once()
    mock_handler_instance.handle_call.assert_awaited_with(
        config=server_config1,
        remote_tool_name="list_tools",
        arguments={}
    )
    mock_tool_registry_instance.register_tool.assert_called_once_with(ANY)
    
    registered_def_arg = mock_tool_registry_instance.register_tool.call_args[0][0]
    assert isinstance(registered_def_arg, ToolDefinition)
    assert registered_def_arg.name == "s1_toolA"
    
    # Assert internal state is correct
    assert "stale_server" not in registrar._registered_tools_by_server
    registered_tools = registrar.get_registered_tools_for_server("server1")
    assert len(registered_tools) == 1
    assert registered_tools[0].name == "s1_toolA"

@pytest.mark.asyncio
async def test_discover_and_register_tools_targeted(mock_dependencies):
    """Tests passing a specific config, ensuring old tools for that server are unregistered."""
    registrar = mock_dependencies["registrar"]
    mock_config_instance = mock_dependencies["config_service"]
    mock_tool_registry_instance = mock_dependencies["tool_registry"]
    mock_handler_instance = mock_dependencies["stdio_handler"]
    
    target_config = StdioMcpServerConfig(server_id="target_server", command="cmd_target", enabled=True, tool_name_prefix="tgt_")

    # Prime the registrar to simulate that this server had old tools registered
    old_tool_def = MagicMock(spec=ToolDefinition)
    old_tool_def.name = "tgt_old_tool"
    registrar._registered_tools_by_server["target_server"] = [old_tool_def]

    # Mock the new tools to be discovered
    remote_tool_meta = MockMcpToolType()
    remote_tool_meta.name = "targetTool"
    remote_tool_meta.description = "Target tool description"
    remote_tool_meta.inputSchema = {}
    list_tools_result = MockMcpListToolsResult()
    list_tools_result.tools = [remote_tool_meta]
    mock_handler_instance.handle_call.return_value = list_tools_result
    
    # Act
    await registrar.discover_and_register_tools(mcp_config=target_config)

    # --- Assertions ---
    # Assert that the old tool was unregistered
    mock_tool_registry_instance.unregister_tool.assert_called_once_with("tgt_old_tool")
    
    # Assert the rest of the flow
    mock_config_instance.add_config.assert_called_once_with(target_config)
    mock_handler_instance.handle_call.assert_awaited_with(config=target_config, remote_tool_name="list_tools", arguments={})
    mock_tool_registry_instance.register_tool.assert_called_once()
    
    # Assert internal state is correct
    assert "target_server" in registrar._registered_tools_by_server
    assert len(registrar.get_all_registered_mcp_tools()) == 1
    assert registrar.get_all_registered_mcp_tools()[0].name == "tgt_targetTool"

@pytest.mark.asyncio
async def test_discover_and_register_handler_fails(mock_dependencies):
    """Tests that a failure in the handler is caught gracefully."""
    registrar = mock_dependencies["registrar"]
    mock_config_instance = mock_dependencies["config_service"]
    mock_tool_registry_instance = mock_dependencies["tool_registry"]
    mock_handler_instance = mock_dependencies["stdio_handler"]
    
    server_config1 = StdioMcpServerConfig(server_id="server_err", command="cmd", enabled=True)
    mock_config_instance.get_all_configs.return_value = [server_config1]
    
    mock_handler_instance.handle_call.side_effect = RuntimeError("Handler discovery failed")

    await registrar.discover_and_register_tools()
    
    mock_tool_registry_instance.register_tool.assert_not_called()
    assert registrar.get_registered_tools_for_server("server_err") == []

# --- Tests for the new methods ---

def test_is_server_registered(mock_dependencies):
    """Tests the is_server_registered method."""
    registrar = mock_dependencies["registrar"]
    assert registrar.is_server_registered("server1") is False
    registrar._registered_tools_by_server["server1"] = [MagicMock()]
    assert registrar.is_server_registered("server1") is True

def test_unregister_tools_from_server(mock_dependencies):
    """Tests the unregister_tools_from_server method."""
    registrar = mock_dependencies["registrar"]
    mock_tool_registry = mock_dependencies["tool_registry"]

    # Setup: mock a registered server with two tools
    tool_def1 = MagicMock(spec=ToolDefinition); tool_def1.name = "toolA"
    tool_def2 = MagicMock(spec=ToolDefinition); tool_def2.name = "toolB"
    registrar._registered_tools_by_server["server_to_remove"] = [tool_def1, tool_def2]

    # Act
    result = registrar.unregister_tools_from_server("server_to_remove")

    # Assert
    assert result is True
    assert mock_tool_registry.unregister_tool.call_count == 2
    mock_tool_registry.unregister_tool.assert_any_call("toolA")
    mock_tool_registry.unregister_tool.assert_any_call("toolB")
    
    # Assert internal state is cleaned up
    assert not registrar.is_server_registered("server_to_remove")
    
    # Test unregistering a non-existent server
    result_nonexistent = registrar.unregister_tools_from_server("non_existent_server")
    assert result_nonexistent is False

# --- Tests for the list_remote_tools method ---
@pytest.mark.asyncio
async def test_list_remote_tools_previews_without_registration(mock_dependencies):
    """
    Tests that `list_remote_tools` discovers tools but does not register them
    or save the configuration.
    """
    registrar = mock_dependencies["registrar"]
    mock_config_instance = mock_dependencies["config_service"]
    mock_tool_registry_instance = mock_dependencies["tool_registry"]
    mock_handler_instance = mock_dependencies["stdio_handler"]

    preview_config = StdioMcpServerConfig(server_id="preview_server", command="preview_cmd")

    # Mock the remote tool response
    remote_tool_meta = MockMcpToolType()
    remote_tool_meta.name = "previewTool"
    remote_tool_meta.description = "A tool for preview"
    remote_tool_meta.inputSchema = {"type": "object", "properties": {"p1": {"type": "integer"}}}
    list_tools_result = MockMcpListToolsResult()
    list_tools_result.tools = [remote_tool_meta]
    mock_handler_instance.handle_call.return_value = list_tools_result

    # Call the preview method
    tool_defs = await registrar.list_remote_tools(mcp_config=preview_config)

    # --- Assertions for No Side Effects ---
    mock_config_instance.add_config.assert_not_called()
    mock_config_instance.load_config.assert_not_called()
    mock_tool_registry_instance.register_tool.assert_not_called()
    assert not registrar._registered_tools_by_server # Internal cache should be empty

    # --- Assertions for Correct Discovery ---
    mock_handler_instance.handle_call.assert_awaited_with(
        config=preview_config,
        remote_tool_name="list_tools",
        arguments={}
    )
    assert len(tool_defs) == 1
    assert isinstance(tool_defs[0], ToolDefinition)
    assert tool_defs[0].name == "previewTool"
    assert tool_defs[0].description == "A tool for preview"
    assert tool_defs[0].argument_schema.get_parameter("p1").param_type == ParameterType.INTEGER

@pytest.mark.asyncio
async def test_list_remote_tools_raises_on_handler_failure(mock_dependencies):
    """
    Tests that `list_remote_tools` propagates exceptions from the handler.
    """
    registrar = mock_dependencies["registrar"]
    mock_handler_instance = mock_dependencies["stdio_handler"]
    
    preview_config = StdioMcpServerConfig(server_id="preview_server_fail", command="fail_cmd")
    mock_handler_instance.handle_call.side_effect = RuntimeError("Preview connection failed")
    
    with pytest.raises(RuntimeError, match="Preview connection failed"):
        await registrar.list_remote_tools(mcp_config=preview_config)
