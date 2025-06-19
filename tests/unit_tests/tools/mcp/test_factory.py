# file: autobyteus/tests/unit_tests/tools/mcp/test_factory.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.tools.mcp.factory import McpToolFactory
from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.tools.mcp.call_handlers.base_handler import McpCallHandler
from autobyteus.tools.mcp.types import BaseMcpConfig, StdioMcpServerConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_config import ToolConfig

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
def mcp_tool_factory(mock_call_handler, mock_server_config, sample_arg_schema):
    """Provides a fully initialized McpToolFactory instance."""
    return McpToolFactory(
        mcp_server_config=mock_server_config,
        mcp_remote_tool_name="remote_calculator",
        mcp_call_handler=mock_call_handler,
        registered_tool_name="MyCalculator",
        tool_description="A remote calculator tool.",
        tool_argument_schema=sample_arg_schema
    )

def test_factory_initialization(mcp_tool_factory: McpToolFactory):
    """Tests that the factory stores its configuration correctly."""
    assert mcp_tool_factory._mcp_server_config.server_id == "test_server_123"
    assert mcp_tool_factory._mcp_remote_tool_name == "remote_calculator"
    assert mcp_tool_factory._registered_tool_name == "MyCalculator"
    assert "remote calculator" in mcp_tool_factory._tool_description

def test_factory_creates_correct_tool_instance(mcp_tool_factory: McpToolFactory, mock_call_handler, mock_server_config, sample_arg_schema):
    """Tests the create_tool method."""
    dummy_config = ToolConfig(params={"some_other_param": "value"})
    tool_instance = mcp_tool_factory.create_tool(config=dummy_config)

    assert isinstance(tool_instance, GenericMcpTool)

    # Check if the created instance was configured with the factory's context
    assert tool_instance._mcp_server_config == mock_server_config
    assert tool_instance._mcp_remote_tool_name == "remote_calculator"
    assert tool_instance._mcp_call_handler == mock_call_handler
    
    # Check if the instance properties are set correctly by calling the overridden methods
    assert tool_instance.get_name() == "MyCalculator"
    assert tool_instance.get_description() == "A remote calculator tool."
    assert tool_instance.get_argument_schema() == sample_arg_schema
