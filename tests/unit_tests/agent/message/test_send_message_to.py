# file: autobyteus/tests/unit_tests/workflow/tools/test_send_message_to.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent.context import AgentContext
from autobyteus.workflow.context.team_manager import TeamManager
from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent
from autobyteus.tools.parameter_schema import ParameterSchema

@pytest.fixture
def mock_team_manager() -> MagicMock:
    """Provides a mocked TeamManager instance with an async dispatch method."""
    manager = MagicMock(spec=TeamManager)
    manager.dispatch_inter_agent_message_request = AsyncMock()
    return manager

@pytest.fixture
def mock_sender_agent_context() -> MagicMock:
    """Provides a mocked AgentContext for the sending agent."""
    context = MagicMock(spec=AgentContext)
    context.agent_id = "sender_agent_001"
    # The new SendMessageTo gets the communicator via its injected TeamManager,
    # so we don't need to mock custom_data for this purpose.
    return context

@pytest.fixture
def send_message_tool(mock_team_manager: MagicMock) -> SendMessageTo:
    """Provides a SendMessageTo tool instance pre-configured with a mock TeamManager."""
    return SendMessageTo(team_manager=mock_team_manager)

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
    # The schema is simpler now, as it doesn't need to differentiate between ID and role.
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
    with a properly constructed event.
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
async def test_execute_failure_without_team_manager(
    mock_sender_agent_context: AgentContext
):
    """
    Tests that the tool returns a critical error if it's not initialized
    with a TeamManager instance.
    """
    tool_without_manager = SendMessageTo(team_manager=None) # Explicitly create a misconfigured tool
    
    result = await tool_without_manager._execute(
        context=mock_sender_agent_context,
        recipient_name="any", content="any", message_type="any"
    )
    
    assert "Error: Critical error: SendMessageTo tool is not configured for workflow communication." in result

@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_arg_set", [
    {"recipient_name": "", "content": "valid", "message_type": "valid"},
    {"recipient_name": "valid", "content": "  ", "message_type": "valid"},
    {"recipient_name": "valid", "content": "valid", "message_type": None},
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
