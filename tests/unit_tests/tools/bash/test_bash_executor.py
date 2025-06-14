import pytest
import asyncio
import subprocess
from unittest.mock import AsyncMock, patch, Mock 
import xml.sax.saxutils

from autobyteus.tools.registry import default_tool_registry 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

TOOL_NAME = "BashExecutor" 

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
    assert "Executes bash commands" in definition.description 
    assert "Errors during command execution are raised as exceptions." in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 1 

    param_command = schema.get_parameter("command")
    assert isinstance(param_command, ParameterDefinition)
    assert param_command.name == "command"
    assert param_command.param_type == ParameterType.STRING
    assert param_command.required is True
    assert "Parameter 'command' for tool 'BashExecutor'" in param_command.description


def test_bash_executor_tool_usage_xml_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    xml_output = definition.usage_xml 
    
    description = definition.description
    escaped_desc = xml.sax.saxutils.escape(description)
    
    assert f'<command name="{TOOL_NAME}" description="{escaped_desc}">' in xml_output
    assert '<arg name="command" type="string" description="Parameter \'command\' for tool \'BashExecutor\'." required="true" />' in xml_output
    assert '</command>' in xml_output

def test_bash_executor_tool_usage_json_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    json_output = definition.usage_json_dict 

    assert json_output["name"] == TOOL_NAME
    assert "Executes bash commands" in json_output["description"]
    input_schema = json_output["inputSchema"]
    assert input_schema["type"] == "object"
    assert "command" in input_schema["properties"]
    command_prop = input_schema["properties"]["command"]
    assert command_prop["type"] == "string" 
    assert "Parameter 'command' for tool 'BashExecutor'" in command_prop["description"]
    assert "command" in input_schema["required"]

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

@pytest.mark.asyncio
async def test_execute_missing_required_command_arg_raises_value_error(bash_executor_tool_instance, mock_agent_context):
    with pytest.raises(ValueError) as exc_info:
        await bash_executor_tool_instance.execute(mock_agent_context) 
    assert f"Invalid arguments for tool '{TOOL_NAME}'" in str(exc_info.value)
    assert "Required parameter 'command' is missing" in str(exc_info.value)

@pytest.mark.asyncio
async def test_execute_command_failure(bash_executor_tool_instance, mock_agent_context):
    command = "invalid_functional_command_xyz"
    error_message = f"bash: {command}: command not found"

    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", error_message.encode())
        mock_process.returncode = 127 
        mock_subprocess.return_value = mock_process

        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            await bash_executor_tool_instance.execute(mock_agent_context, command=command)
        
        assert exc_info.value.returncode == 127
        assert f"{command}: command not found" in exc_info.value.stderr
