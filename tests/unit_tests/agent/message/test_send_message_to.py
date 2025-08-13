# file: autobyteus/tests/unit_tests/agent/message/test_send_message_to.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context.team_manager import TeamManager
from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
from autobyteus.agent_team.events.agent_team_events import InterAgentMessageRequestEvent
from autobyteus.tools.parameter_schema import ParameterSchema

@pytest.fixture
def mock_team_manager() -> MagicMock:
    """Provides a mocked TeamManager instance with an async dispatch method."""
    manager = MagicMock(spec=TeamManager)
    manager.dispatch_inter_agent_message_request = AsyncMock()
    return manager

@pytest.fixture
def mock_team_context(mock_team_manager: MagicMock) -> MagicMock:
    """Provides a mocked AgentTeamContext that holds the mock TeamManager."""
    team_context = MagicMock(spec=AgentTeamContext)
    team_context.team_manager = mock_team_manager
    return team_context

@pytest.fixture
def mock_sender_agent_context(mock_team_context: MagicMock) -> MagicMock:
    """
    Provides a mocked AgentContext where the custom_data contains the
    necessary team_context for the tool to function.
    """
    context = MagicMock(spec=AgentContext)
    context.agent_id = "sender_agent_001"
    context.custom_data = {"team_context": mock_team_context}
    return context

@pytest.fixture
def send_message_tool() -> SendMessageTo:
    """Provides a stateless SendMessageTo tool instance."""
    return SendMessageTo()

# --- Basic Tool Structure Tests ---

def test_get_name(send_message_tool: SendMessageTo):
    assert send_message_tool.get_name() == "SendMessageTo"

def test_get_description(send_message_tool: SendMessageTo):
    desc = send_message_tool.get_description()
    assert "Sends a message to another agent" in desc
    assert "within the same team" in desc

def test_get_argument_schema(send_message_tool: SendMessageTo):
    schema = send_message_tool.get_argument_schema()
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 3
    
    assert schema.get_parameter("recipient_name").required is True
    assert schema.get_parameter("content").required is True
    assert schema.get_parameter("message_type").required is True

# --- Execution Logic Tests ---

@pytest.mark.asyncio
async def test_execute_success(
    send_message_tool: SendMessageTo, 
    mock_sender_agent_context: AgentContext, 
    mock_team_manager: MagicMock
):
    """
    Tests that a successful execution correctly calls the TeamManager's dispatch method
    with a properly constructed event, retrieving the manager from the context.
    """
    recipient = "Researcher"
    content = "Please find data on topic X."
    msg_type = "TASK_ASSIGNMENT"
    
    result = await send_message_tool._execute(
        context=mock_sender_agent_context,
        recipient_name=recipient,
        content=content,
        message_type=msg_type
    )
    
    assert f"Message dispatch for recipient '{recipient}' has been successfully requested." in result
    
    # Verify that the TeamManager's dispatch method was called correctly
    mock_team_manager.dispatch_inter_agent_message_request.assert_awaited_once()
    
    # Inspect the event that was dispatched
    dispatched_event = mock_team_manager.dispatch_inter_agent_message_request.call_args[0][0]
    assert isinstance(dispatched_event, InterAgentMessageRequestEvent)
    assert dispatched_event.sender_agent_id == mock_sender_agent_context.agent_id
    assert dispatched_event.recipient_name == recipient
    assert dispatched_event.content == content
    assert dispatched_event.message_type == msg_type

@pytest.mark.asyncio
async def test_execute_failure_without_team_context(
    send_message_tool: SendMessageTo
):
    """
    Tests that the tool returns a critical error if it's used in an agent context
    that does not have the 'team_context' available.
    """
    # Create a context that is missing the required custom_data
    context_without_team = MagicMock(spec=AgentContext)
    context_without_team.agent_id = "lonely_agent_002"
    context_without_team.custom_data = {} # Missing "team_context"
    
    result = await send_message_tool._execute(
        context=context_without_team,
        recipient_name="any", content="any", message_type="any"
    )
    
    assert "Error: Critical error: SendMessageTo tool is not configured for team communication." in result

@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_arg_set", [
    {"recipient_name": "", "content": "valid", "message_type": "valid"},
    {"recipient_name": "valid", "content": "  ", "message_type": "valid"},
    {"recipient_name": "valid", "content": "valid", "message_type": ""},
])
async def test_execute_input_validation(
    send_message_tool: SendMessageTo,
    mock_sender_agent_context: AgentContext,
    invalid_arg_set: dict
):
    """
    Tests that the tool's internal validation catches empty or invalid arguments.
    """
    result = await send_message_tool._execute(
        context=mock_sender_agent_context,
        **invalid_arg_set
    )
    
    assert result.startswith("Error:")
