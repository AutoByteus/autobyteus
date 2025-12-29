import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.handlers.inter_agent_message_request_event_handler import InterAgentMessageRequestEventHandler
from autobyteus.agent_team.events.agent_team_events import InterAgentMessageRequestEvent, AgentTeamErrorEvent
from autobyteus.agent_team.context import AgentTeamContext
from autobyteus.agent.agent import Agent
from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.agent_team.agent_team import AgentTeam # Added for sub-team type
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage # Added for sub-team message type

@pytest.fixture
def handler():
    return InterAgentMessageRequestEventHandler()

@pytest.fixture
def event():
    return InterAgentMessageRequestEvent(
        sender_agent_id="sender_agent_id_123",
        recipient_name="Recipient",
        content="Do the thing",
        message_type="TASK_ASSIGNMENT"
    )

@pytest.mark.asyncio
async def test_handle_success(handler: InterAgentMessageRequestEventHandler, event: InterAgentMessageRequestEvent, agent_team_context: AgentTeamContext, mock_agent: Agent):
    """
    Tests the happy path where the handler gets a ready agent from TeamManager and posts a message.
    """
    mock_agent.context.config.role = "RecipientRole"
    # Make the mock TeamManager's async method return our mock agent
    agent_team_context.team_manager.ensure_node_is_ready = AsyncMock(return_value=mock_agent)

    await handler.handle(event, agent_team_context)

    # Assert that the handler correctly awaited the team manager
    agent_team_context.team_manager.ensure_node_is_ready.assert_awaited_once_with(name_or_agent_id=event.recipient_name)
    
    # Assert that the message was posted to the now-ready agent
    mock_agent.post_inter_agent_message.assert_awaited_once()
    posted_message = mock_agent.post_inter_agent_message.call_args.args[0]
    assert isinstance(posted_message, InterAgentMessage)
    assert posted_message.content == event.content
    assert posted_message.sender_agent_id == event.sender_agent_id
    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_handle_success_sub_team_recipient(handler: InterAgentMessageRequestEventHandler, event: InterAgentMessageRequestEvent, agent_team_context: AgentTeamContext):
    """
    Tests the path where the recipient of the inter-agent message is a sub-team.
    The handler should post an AgentInputUserMessage to the sub-team.
    """
    mock_sub_team = MagicMock(spec=AgentTeam)
    mock_sub_team.post_message = AsyncMock() # Mock the post_message method on the sub-team
    
    # Make the mock TeamManager's async method return our mock sub-team
    agent_team_context.team_manager.ensure_node_is_ready = AsyncMock(return_value=mock_sub_team)

    await handler.handle(event, agent_team_context)

    # Assert that the handler correctly awaited the team manager
    agent_team_context.team_manager.ensure_node_is_ready.assert_awaited_once_with(name_or_agent_id=event.recipient_name)
    
    # Assert that an AgentInputUserMessage was posted to the sub-team
    mock_sub_team.post_message.assert_awaited_once()
    posted_message = mock_sub_team.post_message.call_args.args[0]
    assert isinstance(posted_message, AgentInputUserMessage)
    assert posted_message.content == event.content
    # Sub-team messages don't have sender_agent_id/recipient_role, they are user input.
    # So we only check the content matches.

@pytest.mark.asyncio
async def test_handle_agent_not_found_or_failed_to_start(handler: InterAgentMessageRequestEventHandler, event: InterAgentMessageRequestEvent, agent_team_context: AgentTeamContext, mock_agent: Agent, caplog):
    """
    Tests the failure path where TeamManager raises an exception (agent not found or failed to start).
    """
    agent_team_context.team_manager.ensure_node_is_ready = AsyncMock(side_effect=Exception("Test Failure"))
    
    await handler.handle(event, agent_team_context)
    
    # Verify we logged the failure
    assert f"Recipient node '{event.recipient_name}' not found or failed to start" in caplog.text
    # Verify we did NOT attempt to post a message
    mock_agent.post_inter_agent_message.assert_not_awaited()
    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_team_context.state.input_event_queues.enqueue_internal_system_event.call_args.args[0]
    assert isinstance(enqueued_event, AgentTeamErrorEvent)
