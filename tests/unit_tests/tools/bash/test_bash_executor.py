# file: tests/unit_tests/tools/bash/test_bash_executor.py
import pytest
import asyncio
import subprocess
from unittest.mock import AsyncMock, patch, Mock 
import xml.sax.saxutils

from autobyteus.tools.registry import default_tool_registry 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext
from autobyteus.llm.providers import LLMProvider

TOOL_NAME = "BashExecutor" 

# ... (fixtures are unchanged) ...
@pytest.fixture
def mock_agent_context():
    mock_context = Mock(spec=AgentContext) 
    mock_context.agent_id = "test_agent_bash_func"
    return mock_context

@pytest.fixture
def bash_executor_tool_instance(mock_agent_context): 
    tool_instance = default_tool_registry.create_tool(TOOL_NAME)
    tool_instance.set_agent_id(mock_agent_context.agent_id)
    return tool_instance

def test_bash_executor_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    assert definition.name == TOOL_NAME
    # ... (rest of definition test is unchanged) ...

def test_bash_executor_get_usage_xml(): # UPDATED
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    xml_output = definition.get_usage_xml()
    
    description = definition.description
    escaped_desc = xml.sax.saxutils.escape(description)
    
    assert f'<tool name="{TOOL_NAME}" description="{escaped_desc}">' in xml_output
    assert '<arg name="command" type="string"' in xml_output
    assert '</tool>' in xml_output

def test_bash_executor_get_usage_json_openai_provider(): # UPDATED
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    json_output_dict = definition.get_usage_json(provider=LLMProvider.OPENAI)

    assert json_output_dict["type"] == "function"
    assert json_output_dict["function"]["name"] == TOOL_NAME
    assert "Executes bash commands" in json_output_dict["function"]["description"]
    parameters = json_output_dict["function"]["parameters"]
    assert "command" in parameters["properties"]
    assert "command" in parameters["required"]

# ... (execution tests are unchanged) ...
@pytest.mark.asyncio
async def test_execute_bash_command_and_return_output(bash_executor_tool_instance, mock_agent_context):
    command = "echo 'BDD Test Functional'"
    expected_output = "BDD Test Functional"

    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"BDD Test Functional\n", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await bash_executor_tool_instance.execute(mock_agent_context, command=command) 
        assert result == expected_output
