# file: autobyteus/tests/unit_tests/tools/mcp/test_registrar.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.tools.mcp.registrar import McpToolRegistrar
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.types import StdioMcpServerConfig, McpTransportType
from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

# Mock external mcp.types
MockMcpToolType = MagicMock()
MockMcpListToolsResult = MagicMock()

@pytest.fixture(autouse=True)
def clear_singleton_cache():
    """Fixture to automatically clear singleton caches before each test."""
    # This ensures that each test gets a fresh instance of the singleton
    if McpToolRegistrar in McpToolRegistrar._instances:
        del McpToolRegistrar._instances[McpToolRegistrar]
    yield
    if McpToolRegistrar in McpToolRegistrar._instances:
        del McpToolRegistrar._instances[McpToolRegistrar]


@pytest.mark.asyncio
async def test_discover_and_register_tools_full_scan():
    """Tests the default behavior of scanning all configured servers."""
    with patch('autobyteus.tools.mcp.registrar.McpConfigService') as MockConfigService, \
         patch('autobyteus.tools.mcp.registrar.ToolRegistry') as MockToolRegistry, \
         patch('autobyteus.tools.mcp.registrar.StdioMcpCallHandler') as MockStdioHandler:

        # Get the mock instances that will be returned when the singletons are instantiated
        mock_config_instance = MockConfigService.return_value
        mock_tool_registry_instance = MockToolRegistry.return_value
        mock_handler_instance = MockStdioHandler.return_value

        # Now, instantiate the registrar. Its __init__ will call the patched classes,
        # receiving our mock instances.
        registrar = McpToolRegistrar()

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

        # We are using the real McpToolFactory and McpSchemaMapper, as they are stateless helpers.
        await registrar.discover_and_register_tools()

        # --- Assertions ---
        mock_config_instance.get_all_configs.assert_called_once()
        
        mock_handler_instance.handle_call.assert_awaited_once_with(
            config=server_config1,
            remote_tool_name="list_tools",
            arguments={}
        )

        mock_tool_registry_instance.register_tool.assert_called_once()
        
        registered_def_arg = mock_tool_registry_instance.register_tool.call_args[0][0]
        assert isinstance(registered_def_arg, ToolDefinition)
        assert registered_def_arg.name == "s1_toolA"
        
        # Test the registrar's internal cache
        registered_tools = registrar.get_registered_tools_for_server("server1")
        assert len(registered_tools) == 1
        assert isinstance(registered_tools[0], ToolDefinition)
        assert registered_tools[0].name == "s1_toolA"
        assert registrar.get_registered_tools_for_server("non_existent_server") == []

@pytest.mark.asyncio
async def test_discover_and_register_tools_targeted():
    """Tests passing a specific config object to discover only one server."""
    with patch('autobyteus.tools.mcp.registrar.McpConfigService') as MockConfigService, \
         patch('autobyteus.tools.mcp.registrar.ToolRegistry') as MockToolRegistry, \
         patch('autobyteus.tools.mcp.registrar.StdioMcpCallHandler') as MockStdioHandler:
        
        mock_config_instance = MockConfigService.return_value
        mock_tool_registry_instance = MockToolRegistry.return_value
        mock_handler_instance = MockStdioHandler.return_value
        
        registrar = McpToolRegistrar()
        
        target_config = StdioMcpServerConfig(server_id="target_server", command="cmd_target", enabled=True, tool_name_prefix="tgt_")

        remote_tool_meta = MockMcpToolType()
        remote_tool_meta.name = "targetTool"
        remote_tool_meta.description = "Target tool description"
        remote_tool_meta.inputSchema = {}
        list_tools_result = MockMcpListToolsResult()
        list_tools_result.tools = [remote_tool_meta]
        mock_handler_instance.handle_call.return_value = list_tools_result
        
        await registrar.discover_and_register_tools(mcp_config=target_config)

        # Assert that the registrar adds the config to the service
        mock_config_instance.add_config.assert_called_once_with(target_config)
        mock_config_instance.get_all_configs.assert_not_called()
        
        mock_handler_instance.handle_call.assert_awaited_once_with(
            config=target_config,
            remote_tool_name="list_tools",
            arguments={}
        )
        mock_tool_registry_instance.register_tool.assert_called_once()
        
        assert "target_server" in registrar._registered_tools_by_server
        assert len(registrar.get_registered_tools_for_server("target_server")) == 1
        assert registrar.get_registered_tools_for_server("target_server")[0].name == "tgt_targetTool"

@pytest.mark.asyncio
async def test_discover_and_register_tools_targeted_with_dict():
    """Tests passing a specific raw config dictionary."""
    with patch('autobyteus.tools.mcp.registrar.McpConfigService') as MockConfigService, \
         patch('autobyteus.tools.mcp.registrar.ToolRegistry') as MockToolRegistry, \
         patch('autobyteus.tools.mcp.registrar.StdioMcpCallHandler') as MockStdioHandler:
        
        mock_config_instance = MockConfigService.return_value
        mock_tool_registry_instance = MockToolRegistry.return_value
        mock_handler_instance = MockStdioHandler.return_value
        
        registrar = McpToolRegistrar()
        
        target_config_dict = {
            "target_server_dict": {
                "transport_type": "stdio",
                "enabled": True,
                "command": "cmd_target_dict"
            }
        }
        
        # The mock config service should return a validated config object when load_config is called
        validated_config = StdioMcpServerConfig(server_id="target_server_dict", command="cmd_target_dict")
        mock_config_instance.load_config.return_value = validated_config

        # Mock the remote tool response
        remote_tool_meta = MockMcpToolType()
        remote_tool_meta.name = "targetToolFromDict"
        remote_tool_meta.description = "Target tool from dict"
        remote_tool_meta.inputSchema = {}
        list_tools_result = MockMcpListToolsResult()
        list_tools_result.tools = [remote_tool_meta]
        mock_handler_instance.handle_call.return_value = list_tools_result
        
        # Call the method with the dictionary
        await registrar.discover_and_register_tools(mcp_config=target_config_dict)

        # Assert that the registrar uses load_config, not add_config or get_all_configs
        mock_config_instance.load_config.assert_called_once_with(target_config_dict)
        mock_config_instance.add_config.assert_not_called()
        mock_config_instance.get_all_configs.assert_not_called()
        
        # Assert the rest of the flow
        mock_handler_instance.handle_call.assert_awaited_once_with(
            config=validated_config,
            remote_tool_name="list_tools",
            arguments={}
        )
        mock_tool_registry_instance.register_tool.assert_called_once()
        
        registered_def_arg = mock_tool_registry_instance.register_tool.call_args[0][0]
        assert registered_def_arg.name == "targetToolFromDict"
        
        # Check internal state
        assert "target_server_dict" in registrar._registered_tools_by_server
        assert len(registrar.get_registered_tools_for_server("target_server_dict")) == 1
        assert registrar.get_all_registered_mcp_tools()[0].name == "targetToolFromDict"


@pytest.mark.asyncio
async def test_discover_and_register_handler_fails():
    """Tests that a failure in the handler is caught gracefully."""
    with patch('autobyteus.tools.mcp.registrar.McpConfigService') as MockConfigService, \
         patch('autobyteus.tools.mcp.registrar.ToolRegistry') as MockToolRegistry, \
         patch('autobyteus.tools.mcp.registrar.StdioMcpCallHandler') as MockStdioHandler:

        mock_config_instance = MockConfigService.return_value
        mock_tool_registry_instance = MockToolRegistry.return_value
        mock_handler_instance = MockStdioHandler.return_value
        
        registrar = McpToolRegistrar()
        
        server_config1 = StdioMcpServerConfig(server_id="server_err", command="cmd", enabled=True)
        mock_config_instance.get_all_configs.return_value = [server_config1]
        
        mock_handler_instance.handle_call.side_effect = RuntimeError("Handler discovery failed")

        await registrar.discover_and_register_tools()
        
        mock_tool_registry_instance.register_tool.assert_not_called()
        assert registrar.get_registered_tools_for_server("server_err") == []
