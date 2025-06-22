# file: autobyteus/tests/unit_tests/tools/mcp/test_registrar.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.tools.mcp.registrar import McpToolRegistrar
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.schema_mapper import McpSchemaMapper
from autobyteus.tools.mcp.types import StdioMcpServerConfig, McpTransportType
from autobyteus.tools.mcp.call_handlers import StdioMcpCallHandler
from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

# Mock external mcp.types
MockMcpToolType = MagicMock()
MockMcpListToolsResult = MagicMock()

@pytest.fixture
def mock_config_service():
    return MagicMock(spec=McpConfigService)

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
# Use autospec=True to ensure mocks have the same signature as the real objects,
# including making async methods return AsyncMocks. This fixes the AttributeError
# for 'assert_awaited_once_with'.
@patch('autobyteus.tools.mcp.registrar.StdioMcpCallHandler', autospec=True)
@patch('autobyteus.tools.mcp.registrar.StreamableHttpMcpCallHandler', autospec=True)
@patch('autobyteus.tools.mcp.registrar.SseMcpCallHandler', autospec=True)
def registrar(MockSse, MockHttp, MockStdio, mock_config_service, mock_schema_mapper, mock_tool_registry) -> McpToolRegistrar:
    # This patching allows us to control the handler instances inside the registrar
    return McpToolRegistrar(
        config_service=mock_config_service,
        schema_mapper=mock_schema_mapper,
        tool_registry=mock_tool_registry
    )

@pytest.mark.asyncio
async def test_discover_and_register_tools_success(registrar: McpToolRegistrar, mock_config_service, mock_schema_mapper, mock_tool_registry):
    server_config1 = StdioMcpServerConfig(
        server_id="server1", 
        command="cmd1", 
        enabled=True,
        tool_name_prefix="s1_"
    )
    # The transport_type is set automatically in the dataclass's __post_init__
    mock_config_service.get_all_configs.return_value = [server_config1]

    # Mock the handler that the registrar will use. Because of autospec=True, this is a mock
    # of the StdioMcpCallHandler class, and its instance methods are AsyncMocks.
    mock_stdio_handler = registrar._handler_registry[McpTransportType.STDIO]
    
    # Mocking mcp.types.Tool structure
    remote_tool1_meta = MockMcpToolType()
    remote_tool1_meta.name = "toolA"
    remote_tool1_meta.description = "Tool A description"
    remote_tool1_meta.inputSchema = {"type": "object", "properties": {"paramA": {"type": "string"}}}
    
    list_tools_result = MockMcpListToolsResult()
    list_tools_result.tools = [remote_tool1_meta]
    
    # The handler's handle_call method is what we need to mock
    mock_stdio_handler.handle_call.return_value = list_tools_result
    
    mapped_schema_tool1 = ParameterSchema()
    mapped_schema_tool1.add_parameter(ParameterDefinition(name="paramA", param_type=ParameterType.STRING, description="..."))
    mock_schema_mapper.map_to_autobyteus_schema.return_value = mapped_schema_tool1

    # Patch McpToolFactory to check its inputs
    with patch('autobyteus.tools.mcp.registrar.McpToolFactory') as MockMcpFactory:
        await registrar.discover_and_register_tools()

        mock_config_service.get_all_configs.assert_called_once()
        
        # Assert that the handler was called correctly for discovery
        mock_stdio_handler.handle_call.assert_awaited_once_with(
            config=server_config1,
            remote_tool_name="list_tools",
            arguments={}
        )

        mock_schema_mapper.map_to_autobyteus_schema.assert_called_once_with(remote_tool1_meta.inputSchema)
        
        # Assert that the factory was instantiated with the correct handler
        MockMcpFactory.assert_called_once_with(
            mcp_server_config=server_config1,
            mcp_remote_tool_name='toolA',
            mcp_call_handler=mock_stdio_handler,
            registered_tool_name='s1_toolA',
            tool_description='Tool A description',
            tool_argument_schema=mapped_schema_tool1
        )

        mock_tool_registry.register_tool.assert_called_once()
        registered_def_arg = mock_tool_registry.register_tool.call_args[0][0]
        assert isinstance(registered_def_arg, ToolDefinition)

@pytest.mark.asyncio
async def test_discover_and_register_handler_fails(registrar: McpToolRegistrar, mock_config_service, mock_tool_registry):
    server_config1 = StdioMcpServerConfig(server_id="server_err", command="cmd", enabled=True)
    mock_config_service.get_all_configs.return_value = [server_config1]
    
    mock_stdio_handler = registrar._handler_registry[McpTransportType.STDIO]
    mock_stdio_handler.handle_call.side_effect = RuntimeError("Handler discovery failed")

    await registrar.discover_and_register_tools()
    mock_tool_registry.register_tool.assert_not_called()
