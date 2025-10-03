import pytest
from typing import Dict, Optional, Any

from ._test_helpers import MockTool 

from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext, AgentConfig
from unittest.mock import MagicMock 


@pytest.fixture
def mock_tool_alpha() -> MockTool:
    """Provides a simple mock tool named 'AlphaTool'."""
    return MockTool(
        name="AlphaTool", 
        description="Description for Alpha.",
        xml_output="<command name=\"AlphaTool\" description=\"Description for Alpha.\"></command>"
    )

@pytest.fixture
def mock_tool_beta() -> MockTool:
    """Provides another mock tool named 'BetaTool' with arguments."""
    beta_schema = ParameterSchema() 
    beta_schema.add_parameter(ParameterDefinition(name="param1", param_type=ParameterType.STRING, description="First param for Beta.", required=True))
    return MockTool(
        name="BetaTool", 
        description="Description for Beta.",
        args_schema=beta_schema,
        xml_output='<command name="BetaTool" description="Description for Beta.">\n  <arg name="param1" type="string" required="true">First param for Beta.</arg>\n</command>'
    )

@pytest.fixture
def mock_tool_empty_xml() -> MockTool:
    """A mock tool that returns an empty string for its XML representation."""
    return MockTool(
        name="EmptyXmlTool", 
        description="This tool returns empty XML.", 
        xml_output="",
        json_output={"name": "EmptyXmlTool", "description": "This tool aims for empty JSON schema.", "input_schema": {"type": "object", "properties": {}}}
    )

@pytest.fixture
def mock_tool_xml_error() -> MockTool:
    """A mock tool whose tool_usage_xml() method raises an error."""
    return MockTool(
        name="XmlErrorTool", 
        description="This tool errors on XML generation.", 
        xml_should_raise=RuntimeError("Simulated XML generation failure")
    )

@pytest.fixture
def mock_tool_json_error() -> MockTool:
    """A mock tool whose tool_usage_json() method raises an error."""
    return MockTool(
        name="JsonErrorTool",
        description="This tool errors on JSON generation.",
        json_should_raise=RuntimeError("Simulated JSON generation failure")
    )

@pytest.fixture
def mock_context_for_system_prompt_processors_factory():
    """
    Factory fixture to create a mock AgentContext for system prompt processor tests.
    Allows specifying the use_xml_tool_format flag.
    """
    def _factory(use_xml_format: bool = True):
        mock_config = MagicMock(spec=AgentConfig)
        mock_config.use_xml_tool_format = use_xml_format
        mock_config.name = "test_config_for_spp"
        mock_config.role = "spp_tester"

        mock_context = MagicMock(spec=AgentContext)
        mock_context.agent_id = "spp_agent_123"
        mock_context.config = mock_config
        mock_context.custom_data = {}
        return mock_context
    return _factory
