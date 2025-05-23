import pytest
import asyncio
from unittest.mock import Mock, patch
from autobyteus.tools.registry import default_tool_registry 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

TOOL_NAME_ASK_USER = "AskUserInput"

@pytest.fixture
def mock_agent_context_ask_user(): 
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_ask_user_func"
    return mock_context

@pytest.fixture
def ask_user_tool_instance(mock_agent_context_ask_user): 
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_ASK_USER)
    tool_instance.set_agent_id(mock_agent_context_ask_user.agent_id)
    return tool_instance

def test_ask_user_input_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_ASK_USER)
    assert definition is not None
    assert definition.name == TOOL_NAME_ASK_USER
    assert "Requests input from the user" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 1 
    
    param_request = schema.get_parameter("request")
    assert isinstance(param_request, ParameterDefinition)
    assert param_request.name == "request"
    assert param_request.param_type == ParameterType.STRING
    assert param_request.required is True
    assert "Parameter 'request' for tool 'AskUserInput'" in param_request.description

def test_ask_user_input_tool_usage_xml_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_ASK_USER)
    xml_output = definition.usage_xml
    assert f'<command name="{TOOL_NAME_ASK_USER}">' in xml_output
    assert '<arg name="request" type="string" description="Parameter \'request\' for tool \'AskUserInput\'." required="true" />' in xml_output

def test_ask_user_input_tool_usage_json_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_ASK_USER)
    json_output = definition.usage_json_dict
    assert json_output["name"] == TOOL_NAME_ASK_USER
    assert "Requests input from the user" in json_output["description"]
    input_schema = json_output["inputSchema"]
    assert "request" in input_schema["properties"]

@pytest.mark.asyncio
async def test_execute_missing_request_arg(ask_user_tool_instance, mock_agent_context_ask_user):
    with pytest.raises(ValueError, match=f"Invalid arguments for tool '{TOOL_NAME_ASK_USER}'"):
        await ask_user_tool_instance.execute(mock_agent_context_ask_user)

@pytest.mark.asyncio
async def test_execute_gets_user_input(ask_user_tool_instance, mock_agent_context_ask_user):
    prompt_text = "What is your functional name?"
    user_response = "Functional Test User"

    with patch('builtins.input', return_value=user_response) as mock_builtin_input:
        mock_loop = Mock(spec=asyncio.AbstractEventLoop)
        async def mock_run_in_executor_direct_call(executor, func, *args):
            return func(*args) 

        with patch('asyncio.get_event_loop', return_value=mock_loop):
            mock_loop.run_in_executor = mock_run_in_executor_direct_call
            actual_response = await ask_user_tool_instance.execute(
                mock_agent_context_ask_user, 
                request=prompt_text
            )
    
    assert actual_response == user_response
    expected_prompt_to_user = f"LLM Agent ({mock_agent_context_ask_user.agent_id}): {prompt_text}\nUser: "
    mock_builtin_input.assert_called_once_with(expected_prompt_to_user)

@pytest.mark.asyncio
async def test_execute_keyboard_interrupt(ask_user_tool_instance, mock_agent_context_ask_user):
    prompt_text = "Functional interrupt test?"
    with patch('builtins.input', side_effect=KeyboardInterrupt):
        mock_loop = Mock(spec=asyncio.AbstractEventLoop)
        async def mock_run_in_executor_direct_call(executor, func, *args):
            return func(*args)
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            mock_loop.run_in_executor = mock_run_in_executor_direct_call
            actual_response = await ask_user_tool_instance.execute(
                mock_agent_context_ask_user, request=prompt_text
            )
    assert actual_response == "[Input process interrupted by user]"

@pytest.mark.asyncio
async def test_execute_eof_error(ask_user_tool_instance, mock_agent_context_ask_user):
    prompt_text = "Functional EOF test:"
    with patch('builtins.input', side_effect=EOFError):
        mock_loop = Mock(spec=asyncio.AbstractEventLoop)
        async def mock_run_in_executor_direct_call(executor, func, *args):
            return func(*args)
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            mock_loop.run_in_executor = mock_run_in_executor_direct_call
            actual_response = await ask_user_tool_instance.execute(
                mock_agent_context_ask_user, request=prompt_text
            )
    assert actual_response == "[EOF error occurred during input]"
