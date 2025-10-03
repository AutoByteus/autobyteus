# file: autobyteus/tests/unit_tests/tools/mcp/test_factory.py
import pytest
from unittest.mock import MagicMock

from autobyteus.tools.mcp.factory import McpToolFactory
from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_config import ToolConfig

@pytest.fixture
def sample_arg_schema():
    """Provides a sample ParameterSchema for tool arguments."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="param1", param_type=ParameterType.STRING, description="Test param"))
    return schema

@pytest.fixture
def mcp_tool_factory(sample_arg_schema):
    """Provides a fully initialized McpToolFactory instance using the new signature."""
    return McpToolFactory(
        server_id="test_server_123",
        remote_tool_name="remote_calculator",
        registered_tool_name="MyCalculator",
        tool_description="A remote calculator tool.",
        tool_argument_schema=sample_arg_schema
    )

def test_factory_initialization(mcp_tool_factory: McpToolFactory):
    """Tests that the factory stores its configuration identifiers correctly."""
    assert mcp_tool_factory._server_id == "test_server_123"
    assert mcp_tool_factory._remote_tool_name == "remote_calculator"
    assert mcp_tool_factory._registered_tool_name == "MyCalculator"
    assert "remote calculator" in mcp_tool_factory._tool_description
    assert mcp_tool_factory._tool_argument_schema is not None

def test_factory_creates_correct_tool_instance(mcp_tool_factory: McpToolFactory, sample_arg_schema):
    """Tests that the create_tool method correctly instantiates and configures a GenericMcpTool."""
    # The config passed to create_tool should be ignored by this factory, but we test it for completeness.
    dummy_config = ToolConfig(params={"some_other_param": "value"})
    tool_instance = mcp_tool_factory.create_tool(config=dummy_config)

    # 1. Verify the created object is of the correct type
    assert isinstance(tool_instance, GenericMcpTool)

    # 2. Check if the created instance was configured with the factory's identifiers
    assert tool_instance._server_id == "test_server_123"
    assert tool_instance._remote_tool_name == "remote_calculator"
    
    # 3. Check if the instance properties are set correctly by calling the overridden methods
    assert tool_instance.get_name() == "MyCalculator"
    assert tool_instance.get_description() == "A remote calculator tool."
    assert tool_instance.get_argument_schema() == sample_arg_schema
