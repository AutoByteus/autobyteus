# file: autobyteus/tests/unit_tests/tools/mcp/test_generic_mcp_tool.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

@pytest.fixture
def sample_arg_schema():
    """Provides a sample ParameterSchema for tool arguments."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="param1", param_type=ParameterType.STRING, description="Test param"))
    return schema

@pytest.fixture
def generic_mcp_tool_instance(sample_arg_schema):
    """Provides a fully initialized instance of GenericMcpTool with the new signature."""
    return GenericMcpTool(
        server_id="test_server_123",
        remote_tool_name="remote_calculator",
        name="MyCalculator",
        description="A remote calculator tool.",
        argument_schema=sample_arg_schema
    )

@pytest.fixture
def mock_agent_context():
    """Provides a mock AgentContext."""
    ctx = MagicMock(spec=AgentContext)
    ctx.agent_id = "test_agent_001"
    return ctx

def test_generic_mcp_tool_properties(generic_mcp_tool_instance: GenericMcpTool, sample_arg_schema):
    """Tests that the instance methods return the specific data they were initialized with."""
    # Test that the instance methods are correctly overridden to return specific data
    assert generic_mcp_tool_instance.get_name() == "MyCalculator"
    assert generic_mcp_tool_instance.get_description() == "A remote calculator tool."
    assert generic_mcp_tool_instance.get_argument_schema() == sample_arg_schema
    
    # Test the base class's static methods for sanity check
    assert GenericMcpTool.get_name() == "GenericMcpTool"
    assert "generic wrapper" in GenericMcpTool.get_description()
    assert GenericMcpTool.get_argument_schema() is None

@pytest.mark.asyncio
async def test_execute_success(generic_mcp_tool_instance: GenericMcpTool, mock_agent_context, mocker):
    """
    Tests that the _execute method correctly instantiates a proxy and delegates the call.
    """
    # 1. Setup the mock for McpServerProxy
    mock_proxy_class = mocker.patch('autobyteus.tools.mcp.tool.McpServerProxy')
    mock_proxy_instance = mock_proxy_class.return_value
    
    expected_result = {"result": "calculation complete"}
    mock_proxy_instance.call_tool = AsyncMock(return_value=expected_result)

    # 2. Define test arguments and execute the tool
    remote_tool_args = {"param1": "value1", "param2": 100}
    result = await generic_mcp_tool_instance._execute(context=mock_agent_context, **remote_tool_args)

    # 3. Assert the outcome
    # Assert that the proxy was instantiated correctly
    mock_proxy_class.assert_called_once_with(
        agent_id=mock_agent_context.agent_id,
        server_id="test_server_123"
    )

    # Assert that the call_tool method on the proxy instance was awaited correctly
    mock_proxy_instance.call_tool.assert_awaited_once_with(
        tool_name="remote_calculator",
        arguments=remote_tool_args
    )
    
    # Assert that the final result is passed through
    assert result == expected_result

@pytest.mark.asyncio
async def test_execute_proxy_fails(generic_mcp_tool_instance: GenericMcpTool, mock_agent_context, mocker):
    """Tests that an exception from the proxy's call_tool is propagated."""
    # 1. Setup the mock to raise an exception
    mock_proxy_class = mocker.patch('autobyteus.tools.mcp.tool.McpServerProxy')
    mock_proxy_instance = mock_proxy_class.return_value
    mock_proxy_instance.call_tool = AsyncMock(side_effect=RuntimeError("Proxy failed"))

    # 2. Execute and assert that the exception is raised
    with pytest.raises(RuntimeError, match="Proxy failed"):
        await generic_mcp_tool_instance._execute(context=mock_agent_context, param1="test")
