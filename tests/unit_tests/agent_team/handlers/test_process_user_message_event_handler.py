# file: autobyteus/tests/unit_tests/agent_team/handlers/test_process_user_message_event_handler.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.handlers.process_user_message_event_handler import ProcessUserMessageEventHandler
from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent, AgentTeamErrorEvent
from autobyteus.agent_team.context import AgentTeamContext
from autobyteus.agent.agent import Agent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

@pytest.fixture
def handler():
    return ProcessUserMessageEventHandler()

@pytest.fixture
def event():
    return ProcessUserMessageEvent(
        user_message=AgentInputUserMessage(content="Hello agent team"),
        target_agent_name="Coordinator"
    )

@pytest.mark.asyncio
async def test_handle_success(handler: ProcessUserMessageEventHandler, event: ProcessUserMessageEvent, agent_team_context: AgentTeamContext, mock_agent: Agent):
    """
    Tests the happy path where TeamManager provides a ready agent.
    """
    agent_team_context.team_manager.ensure_node_is_ready = AsyncMock(return_value=mock_agent)

    await handler.handle(event, agent_team_context)

    agent_team_context.team_manager.ensure_node_is_ready.assert_awaited_once_with(name_or_agent_id="Coordinator")
    mock_agent.post_user_message.assert_awaited_once_with(event.user_message)
    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_handle_agent_not_found(handler: ProcessUserMessageEventHandler, event: ProcessUserMessageEvent, agent_team_context: AgentTeamContext):
    """
    Tests that an error is reported if the TeamManager raises an exception.
    """
    agent_team_context.team_manager.ensure_node_is_ready = AsyncMock(side_effect=Exception("Not Found"))

    await handler.handle(event, agent_team_context)

    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_team_context.state.input_event_queues.enqueue_internal_system_event.call_args.args[0]
    assert isinstance(enqueued_event, AgentTeamErrorEvent)
