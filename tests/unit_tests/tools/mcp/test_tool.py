# file: autobyteus/tests/unit_tests/tools/mcp/test_tool.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.tools.mcp.connection_manager import McpConnectionManager
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext # For type hinting context

# Mock mcp.ClientSession for these tests
MockMcpClientSession = AsyncMock()

@pytest.fixture
def mock_connection_manager():
    return AsyncMock(spec=McpConnectionManager)

@pytest.fixture
def sample_arg_schema():
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="param1", param_type=ParameterType.STRING, description="Test param"))
    return schema

@pytest.fixture
def generic_mcp_tool_instance(mock_connection_manager, sample_arg_schema):
    return GenericMcpTool(
        mcp_server_id="test_server_123",
        mcp_remote_tool_name="remote_calculator",
        mcp_connection_manager=mock_connection_manager,
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
    assert generic_mcp_tool_instance.get_instance_name() == "MyCalculator"
    assert generic_mcp_tool_instance.get_instance_description() == "A remote calculator tool."
    assert generic_mcp_tool_instance.get_instance_argument_schema() == sample_arg_schema
    
    # Test BaseTool static methods (they should return generic info for GenericMcpTool class itself)
    assert GenericMcpTool.get_name() == "GenericMcpTool"
    assert "generic wrapper" in GenericMcpTool.get_description()
    assert GenericMcpTool.get_argument_schema() is None # The class itself has no fixed schema

@pytest.mark.asyncio
async def test_execute_success(generic_mcp_tool_instance: GenericMcpTool, mock_connection_manager, mock_agent_context):
    mock_session = MockMcpClientSession()
    mock_connection_manager.get_session.return_value = mock_session
    
    remote_tool_args = {"param1": "value1", "param2": 100}
    expected_result = {"result": "calculation complete"}
    mock_session.call_tool.return_value = expected_result

    result = await generic_mcp_tool_instance._execute(context=mock_agent_context, **remote_tool_args)

    mock_connection_manager.get_session.assert_awaited_once_with("test_server_123")
    # Verify the positional call, which is the fix.
    mock_session.call_tool.assert_called_once_with("remote_calculator", remote_tool_args)
    assert result == expected_result

@pytest.mark.asyncio
async def test_execute_get_session_fails(generic_mcp_tool_instance: GenericMcpTool, mock_connection_manager, mock_agent_context):
    mock_connection_manager.get_session.side_effect = RuntimeError("Connection failed")
    
    with pytest.raises(RuntimeError, match="Failed to acquire MCP session for server 'test_server_123': Connection failed"):
        await generic_mcp_tool_instance._execute(context=mock_agent_context, param1="test")

@pytest.mark.asyncio
async def test_execute_call_tool_fails(generic_mcp_tool_instance: GenericMcpTool, mock_connection_manager, mock_agent_context):
    mock_session = MockMcpClientSession()
    mock_connection_manager.get_session.return_value = mock_session
    mock_session.call_tool.side_effect = RuntimeError("Remote call error")

    with pytest.raises(RuntimeError, match="Error calling remote MCP tool 'remote_calculator': Remote call error"):
        await generic_mcp_tool_instance._execute(context=mock_agent_context, param1="test")

@pytest.mark.asyncio
async def test_execute_no_connection_manager_set_temporarily(sample_arg_schema, mock_agent_context):
    # Test the internal check if _mcp_connection_manager was None (though constructor requires it)
    tool_instance = GenericMcpTool(
        mcp_server_id="s", mcp_remote_tool_name="r", mcp_connection_manager=None, # type: ignore
        name="n", description="d", argument_schema=sample_arg_schema
    )
    with pytest.raises(RuntimeError, match="McpConnectionManager not available"):
       await tool_instance._execute(context=mock_agent_context)
