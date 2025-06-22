# file: autobyteus/tests/unit_tests/tools/mcp/test_tool.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.tools.mcp.call_handlers.base_handler import McpCallHandler
from autobyteus.tools.mcp.types import StdioMcpServerConfig, BaseMcpConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

@pytest.fixture
def mock_call_handler():
    return AsyncMock(spec=McpCallHandler)

@pytest.fixture
def mock_server_config():
    return StdioMcpServerConfig(server_id="test_server_123", command="test_cmd")

@pytest.fixture
def sample_arg_schema():
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="param1", param_type=ParameterType.STRING, description="Test param"))
    return schema

@pytest.fixture
def generic_mcp_tool_instance(mock_call_handler, mock_server_config, sample_arg_schema):
    return GenericMcpTool(
        mcp_server_config=mock_server_config,
        mcp_remote_tool_name="remote_calculator",
        mcp_call_handler=mock_call_handler,
        name="MyCalculator",
        description="A remote calculator tool.",
        argument_schema=sample_arg_schema
    )

@pytest.fixture
def mock_agent_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.agent_id = "test_agent_001"
    return ctx

def test_generic_mcp_tool_properties(generic_mcp_tool_instance: GenericMcpTool, sample_arg_schema):
    # Test that the instance methods return the specific data they were initialized with
    assert generic_mcp_tool_instance.get_name() == "MyCalculator"
    assert generic_mcp_tool_instance.get_description() == "A remote calculator tool."
    assert generic_mcp_tool_instance.get_argument_schema() == sample_arg_schema
    
    # Test BaseTool static methods
    assert GenericMcpTool.get_name() == "GenericMcpTool"
    assert "generic wrapper" in GenericMcpTool.get_description()
    assert GenericMcpTool.get_argument_schema() is None

@pytest.mark.asyncio
async def test_execute_success(generic_mcp_tool_instance: GenericMcpTool, mock_call_handler, mock_server_config, mock_agent_context):
    remote_tool_args = {"param1": "value1", "param2": 100}
    expected_result = {"result": "calculation complete"}
    mock_call_handler.handle_call.return_value = expected_result

    result = await generic_mcp_tool_instance._execute(context=mock_agent_context, **remote_tool_args)

    mock_call_handler.handle_call.assert_awaited_once_with(
        config=mock_server_config,
        remote_tool_name="remote_calculator",
        arguments=remote_tool_args
    )
    assert result == expected_result

@pytest.mark.asyncio
async def test_execute_handler_fails(generic_mcp_tool_instance: GenericMcpTool, mock_call_handler, mock_agent_context):
    mock_call_handler.handle_call.side_effect = RuntimeError("Handler failed")
    
    with pytest.raises(RuntimeError, match="Handler failed"):
        await generic_mcp_tool_instance._execute(context=mock_agent_context, param1="test")

@pytest.mark.asyncio
async def test_execute_no_handler_set_temporarily(mock_server_config, sample_arg_schema, mock_agent_context):
    tool_instance = GenericMcpTool(
        mcp_server_config=mock_server_config,
        mcp_remote_tool_name="r",
        mcp_call_handler=None, # type: ignore
        name="n", 
        description="d", 
        argument_schema=sample_arg_schema
    )
    with pytest.raises(RuntimeError, match="McpCallHandler not available"):
       await tool_instance._execute(context=mock_agent_context)
