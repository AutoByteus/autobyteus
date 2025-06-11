# file: autobyteus/tests/unit_tests/tools/mcp/test_registrar.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from autobyteus.tools.mcp.registrar import McpToolRegistrar
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.connection_manager import McpConnectionManager
from autobyteus.tools.mcp.schema_mapper import McpSchemaMapper
from autobyteus.tools.mcp.types import StdioMcpServerConfig, McpTransportType
from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.tools.mcp.factory import McpToolFactory

from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.parameter_schema import ParameterDefinition, ParameterSchema, ParameterType

# Mock external mcp.types
MockMcpToolType = MagicMock() # Represents mcp.types.Tool
MockMcpListToolsResult = MagicMock() # Represents mcp.types.ListToolsResult

@pytest.fixture
def mock_config_service():
    return MagicMock(spec=McpConfigService)

@pytest.fixture
def mock_conn_manager():
    return AsyncMock(spec=McpConnectionManager)

@pytest.fixture
def mock_schema_mapper():
    mapper = MagicMock(spec=McpSchemaMapper)
    # Default mock schema to return for simplicity
    mapper.map_to_autobyteus_schema.return_value = ParameterSchema() 
    return mapper

@pytest.fixture
def mock_tool_registry():
    registry = MagicMock(spec=ToolRegistry)
    registry.register_tool = MagicMock()
    return registry

@pytest.fixture
def registrar(mock_config_service, mock_conn_manager, mock_schema_mapper, mock_tool_registry) -> McpToolRegistrar:
    return McpToolRegistrar(
        config_service=mock_config_service,
        conn_manager=mock_conn_manager,
        schema_mapper=mock_schema_mapper,
        tool_registry=mock_tool_registry
    )

@pytest.mark.asyncio
async def test_discover_and_register_tools_success(registrar: McpToolRegistrar, mock_config_service, mock_conn_manager, mock_schema_mapper, mock_tool_registry):
    server_config1 = StdioMcpServerConfig(
        server_id="server1", 
        command="cmd1", 
        enabled=True,
        tool_name_prefix="s1_"
    )
    mock_config_service.get_all_configs.return_value = [server_config1]

    mock_session = AsyncMock()
    mock_conn_manager.get_session.return_value = mock_session

    # Mocking mcp.types.Tool structure
    remote_tool1_meta = MockMcpToolType()
    remote_tool1_meta.name = "toolA"
    remote_tool1_meta.description = "Tool A description"
    remote_tool1_meta.inputSchema = {"type": "object", "properties": {"paramA": {"type": "string"}}}
    
    list_tools_result = MockMcpListToolsResult()
    list_tools_result.tools = [remote_tool1_meta]
    mock_session.list_tools.return_value = list_tools_result
    
    mapped_schema_tool1 = ParameterSchema()
    mapped_schema_tool1.add_parameter(ParameterDefinition(name="paramA", param_type=ParameterType.STRING, description="..."))
    mock_schema_mapper.map_to_autobyteus_schema.return_value = mapped_schema_tool1

    await registrar.discover_and_register_tools()

    mock_config_service.get_all_configs.assert_called_once()
    mock_conn_manager.get_session.assert_awaited_once_with("server1")
    mock_session.list_tools.assert_awaited_once()
    mock_schema_mapper.map_to_autobyteus_schema.assert_called_once_with(remote_tool1_meta.inputSchema)
    
    # Check that ToolRegistry.register_tool was called with a ToolDefinition
    mock_tool_registry.register_tool.assert_called_once()
    registered_def_arg = mock_tool_registry.register_tool.call_args[0][0]
    
    assert isinstance(registered_def_arg, ToolDefinition)
    assert registered_def_arg.name == "s1_toolA" # Prefixed
    assert registered_def_arg.description == "Tool A description"
    assert registered_def_arg.argument_schema == mapped_schema_tool1
    
    # Assert that a factory is used, and no class is specified.
    assert registered_def_arg.tool_class is None
    assert callable(registered_def_arg.custom_factory)


@pytest.mark.asyncio
async def test_discover_and_register_no_configs(registrar: McpToolRegistrar, mock_config_service, mock_conn_manager, mock_tool_registry):
    mock_config_service.get_all_configs.return_value = []
    await registrar.discover_and_register_tools()
    mock_conn_manager.get_session.assert_not_called()
    mock_tool_registry.register_tool.assert_not_called()

@pytest.mark.asyncio
async def test_discover_and_register_disabled_server(registrar: McpToolRegistrar, mock_config_service, mock_conn_manager, mock_tool_registry):
    server_config_disabled = StdioMcpServerConfig(server_id="disabled_server", command="cmd", enabled=False)
    mock_config_service.get_all_configs.return_value = [server_config_disabled]
    
    await registrar.discover_and_register_tools()
    mock_conn_manager.get_session.assert_not_called()
    mock_tool_registry.register_tool.assert_not_called()

@pytest.mark.asyncio
async def test_discover_and_register_get_session_fails(registrar: McpToolRegistrar, mock_config_service, mock_conn_manager, mock_tool_registry):
    server_config1 = StdioMcpServerConfig(server_id="server_err", command="cmd", enabled=True)
    mock_config_service.get_all_configs.return_value = [server_config1]
    mock_conn_manager.get_session.side_effect = RuntimeError("Session connection failed")

    await registrar.discover_and_register_tools() # Should log error but not crash
    mock_tool_registry.register_tool.assert_not_called()

@pytest.mark.asyncio
async def test_discover_and_register_list_tools_fails(registrar: McpToolRegistrar, mock_config_service, mock_conn_manager, mock_tool_registry):
    server_config1 = StdioMcpServerConfig(server_id="server_list_err", command="cmd", enabled=True)
    mock_config_service.get_all_configs.return_value = [server_config1]
    
    mock_session = AsyncMock()
    mock_conn_manager.get_session.return_value = mock_session
    mock_session.list_tools.side_effect = RuntimeError("list_tools API error")

    await registrar.discover_and_register_tools() # Should log error
    mock_tool_registry.register_tool.assert_not_called()

def test_generate_usage_xml(registrar: McpToolRegistrar):
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition("p1", ParameterType.STRING, "Desc 1", True))
    schema.add_parameter(ParameterDefinition("p2", ParameterType.INTEGER, "Desc 2", False, default_value=10))
    xml = registrar._generate_usage_xml("TestTool", "Tool for testing.", schema)
    
    assert "<command name=\"TestTool\">" in xml
    assert "<!-- Description: Tool for testing. -->" in xml
    assert "<arg name=\"p1\" type=\"string\" description=\"Desc 1\" required=\"true\" />" in xml
    assert "<arg name=\"p2\" type=\"integer\" description=\"Desc 2\" required=\"false\" default=\"10\" />" in xml
    assert "</command>" in xml

def test_generate_usage_json(registrar: McpToolRegistrar):
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition("p1", ParameterType.STRING, "Desc 1", True))
    json_dict = registrar._generate_usage_json("TestTool", "Tool for testing.", schema)

    assert json_dict["name"] == "TestTool"
    assert json_dict["description"] == "Tool for testing."
    assert "p1" in json_dict["inputSchema"]["properties"]
    assert json_dict["inputSchema"]["required"] == ["p1"]
