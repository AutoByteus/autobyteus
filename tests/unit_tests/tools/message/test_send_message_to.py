import pytest
from unittest.mock import Mock, AsyncMock, patch
import xml.sax.saxutils
from autobyteus.tools.base_tool import BaseTool # For type checking the tool
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent.context import AgentContext, AgentConfig
from autobyteus.agent.group.agent_group_context import AgentGroupContext
from autobyteus.agent.message.inter_agent_message import InterAgentMessage, InterAgentMessageType
from autobyteus.agent.agent import Agent # For mocking agents
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

@pytest.fixture
def mock_sender_agent_context():
    context = Mock(spec=AgentContext)
    context.agent_id = "sender_agent_001"
    context.custom_data = {}
    return context

@pytest.fixture
def mock_recipient_agent():
    agent = Mock(spec=Agent)
    agent.agent_id = "recipient_agent_007"
    
    # Mock the context and config for the recipient agent
    agent.context = Mock(spec=AgentContext)
    mock_config = Mock(spec=AgentConfig)
    mock_config.role = "worker_bee" # Example role
    agent.context.config = mock_config
    agent.post_inter_agent_message = AsyncMock()
    return agent

@pytest.fixture
def mock_agent_group_context(mock_recipient_agent):
    group_context = Mock(spec=AgentGroupContext)
    group_context.group_id = "test_group"
    
    # Setup mock methods for AgentGroupContext
    def get_agent_side_effect(agent_id_to_find):
        if agent_id_to_find == mock_recipient_agent.agent_id:
            return mock_recipient_agent
        return None
    group_context.get_agent = Mock(side_effect=get_agent_side_effect)

    def get_agents_by_role_side_effect(role_name_to_find):
        if role_name_to_find == mock_recipient_agent.context.config.role:
            return [mock_recipient_agent]
        return []
    group_context.get_agents_by_role = Mock(side_effect=get_agents_by_role_side_effect)
    
    return group_context

@pytest.fixture
def send_message_tool():
    return SendMessageTo()

# Basic Tool Structure Tests
def test_get_name(send_message_tool: SendMessageTo):
    assert send_message_tool.get_name() == SendMessageTo.TOOL_NAME

def test_get_description(send_message_tool: SendMessageTo):
    desc = send_message_tool.get_description()
    assert "Sends a message to another agent" in desc
    assert "within the same group" in desc

def test_get_argument_schema(send_message_tool: SendMessageTo):
    schema = send_message_tool.get_argument_schema()
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 4 # recipient_role_name, content, message_type, recipient_agent_id
    
    assert schema.get_parameter("recipient_role_name").required is True
    assert schema.get_parameter("content").required is True
    assert schema.get_parameter("message_type").required is True
    assert schema.get_parameter("recipient_agent_id").required is False

def test_tool_usage_xml_output(send_message_tool: SendMessageTo):
    xml_output = send_message_tool.tool_usage_xml()
    description = send_message_tool.get_description()
    escaped_desc = xml.sax.saxutils.escape(description)
    assert f'<command name="{SendMessageTo.TOOL_NAME}" description="{escaped_desc}">' in xml_output
    assert '<arg name="recipient_role_name" type="string"' in xml_output
    assert '<arg name="content" type="string"' in xml_output
    assert '<arg name="message_type" type="string"' in xml_output
    assert '<arg name="recipient_agent_id" type="string" required="false"' in xml_output

def test_tool_usage_json_output(send_message_tool: SendMessageTo):
    json_output = send_message_tool.tool_usage_json()
    assert json_output["name"] == SendMessageTo.TOOL_NAME
    assert SendMessageTo.get_description() in json_output["description"]
    input_schema = json_output["inputSchema"]
    assert "recipient_role_name" in input_schema["properties"]
    assert "recipient_agent_id" not in input_schema.get("required", [])

# Execute Tests
@pytest.mark.asyncio
async def test_execute_send_to_specific_id_success(
    send_message_tool: SendMessageTo, 
    mock_sender_agent_context: AgentContext, 
    mock_recipient_agent: Agent,
    mock_agent_group_context: AgentGroupContext
):
    mock_sender_agent_context.custom_data['agent_group_context'] = mock_agent_group_context
    
    result = await send_message_tool.execute(
        context=mock_sender_agent_context,
        recipient_role_name="any_role_here", # Should be overridden by ID
        content="Test message content",
        message_type="TASK_ASSIGNMENT",
        recipient_agent_id=mock_recipient_agent.agent_id
    )
    
    assert "Message successfully sent" in result
    assert mock_recipient_agent.agent_id in result
    mock_recipient_agent.post_inter_agent_message.assert_called_once()
    sent_message: InterAgentMessage = mock_recipient_agent.post_inter_agent_message.call_args[0][0]
    assert sent_message.content == "Test message content"
    assert sent_message.message_type == InterAgentMessageType.TASK_ASSIGNMENT
    assert sent_message.sender_agent_id == mock_sender_agent_context.agent_id
    assert sent_message.recipient_agent_id == mock_recipient_agent.agent_id

@pytest.mark.asyncio
async def test_execute_send_to_role_success(
    send_message_tool: SendMessageTo, 
    mock_sender_agent_context: AgentContext, 
    mock_recipient_agent: Agent,
    mock_agent_group_context: AgentGroupContext
):
    mock_sender_agent_context.custom_data['agent_group_context'] = mock_agent_group_context
    
    result = await send_message_tool.execute(
        context=mock_sender_agent_context,
        recipient_role_name=mock_recipient_agent.context.config.role, # Target by role
        content="Role-based message",
        message_type="CLARIFICATION",
        recipient_agent_id=None # No specific ID
    )
    
    assert "Message successfully sent" in result
    assert mock_recipient_agent.agent_id in result # Should resolve to this agent
    mock_recipient_agent.post_inter_agent_message.assert_called_once()
    sent_message: InterAgentMessage = mock_recipient_agent.post_inter_agent_message.call_args[0][0]
    assert sent_message.content == "Role-based message"
    assert sent_message.message_type == InterAgentMessageType.CLARIFICATION

@pytest.mark.asyncio
async def test_execute_no_group_context(send_message_tool: SendMessageTo, mock_sender_agent_context: AgentContext):
    # custom_data is empty, no agent_group_context
    result = await send_message_tool._execute( # Test _execute directly to bypass arg validation
        context=mock_sender_agent_context,
        recipient_role_name="worker",
        content="Test",
        message_type="TASK"
    )
    assert "Error: AgentGroupContext not found" in result

@pytest.mark.asyncio
async def test_execute_recipient_not_found_by_id_or_role(
    send_message_tool: SendMessageTo, 
    mock_sender_agent_context: AgentContext,
    mock_agent_group_context: AgentGroupContext # Group context that won't find the agent
):
    mock_sender_agent_context.custom_data['agent_group_context'] = mock_agent_group_context
    # Make get_agent and get_agents_by_role return None/empty
    mock_agent_group_context.get_agent = Mock(return_value=None)
    mock_agent_group_context.get_agents_by_role = Mock(return_value=[])

    result = await send_message_tool._execute(
        context=mock_sender_agent_context,
        recipient_role_name="non_existent_role",
        content="To nowhere",
        message_type="INFO",
        recipient_agent_id="non_existent_id"
    )
    assert "Error: No agent found with role 'non_existent_role'" in result

@pytest.mark.asyncio
async def test_execute_invalid_message_type_string(
    send_message_tool: SendMessageTo,
    mock_sender_agent_context: AgentContext,
    mock_agent_group_context: AgentGroupContext,
    mock_recipient_agent: Agent
):
    mock_sender_agent_context.custom_data['agent_group_context'] = mock_agent_group_context
    mock_agent_group_context.get_agent = Mock(return_value=mock_recipient_agent) # Ensure recipient is found

    with patch('autobyteus.agent.message.inter_agent_message.InterAgentMessage.create_with_dynamic_message_type', 
               side_effect=ValueError("Simulated bad message type")) as mock_create:
        result = await send_message_tool._execute(
            context=mock_sender_agent_context,
            recipient_role_name="worker_bee",
            content="Test",
            message_type="VERY_BAD_TYPE_THAT_FAILS_ADD", # This type will cause the mock to raise ValueError
            recipient_agent_id=mock_recipient_agent.agent_id
        )
    assert "Error: Error creating message: Simulated bad message type" in result
    mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_execute_missing_required_args(send_message_tool: SendMessageTo, mock_sender_agent_context: AgentContext):
    # BaseTool.execute will catch these based on the schema
    with pytest.raises(ValueError, match="Invalid arguments for tool 'SendMessageTo'"):
        await send_message_tool.execute(context=mock_sender_agent_context, content="test") # Missing role, type

    with pytest.raises(ValueError, match="Invalid arguments for tool 'SendMessageTo'"):
        await send_message_tool.execute(context=mock_sender_agent_context, recipient_role_name="test", message_type="test") # Missing content
