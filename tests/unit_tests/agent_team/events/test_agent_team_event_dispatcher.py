# file: autobyteus/tests/unit_tests/agent_team/events/test_agent_team_event_dispatcher.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.events.agent_team_event_dispatcher import AgentTeamEventDispatcher
from autobyteus.agent_team.events.agent_team_events import (
    BaseAgentTeamEvent,
    ProcessUserMessageEvent,
    AgentTeamIdleEvent,
    AgentTeamErrorEvent,
)
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage


@pytest.mark.asyncio
async def test_dispatch_logs_warning_when_no_handler(agent_team_context):
    registry = MagicMock()
    registry.get_handler.return_value = None
    dispatcher = AgentTeamEventDispatcher(registry)

    with patch('autobyteus.agent_team.events.agent_team_event_dispatcher.logger') as mock_logger:
        await dispatcher.dispatch(BaseAgentTeamEvent(), agent_team_context)
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_operational_event_enqueues_idle(agent_team_context):
    handler = MagicMock()
    handler.handle = AsyncMock()
    registry = MagicMock()
    registry.get_handler.return_value = handler
    dispatcher = AgentTeamEventDispatcher(registry)

    event = ProcessUserMessageEvent(
        user_message=AgentInputUserMessage(content="hi"),
        target_agent_name="Coordinator",
    )
    await dispatcher.dispatch(event, agent_team_context)

    handler.handle.assert_awaited_once_with(event, agent_team_context)
    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_team_context.state.input_event_queues.enqueue_internal_system_event.call_args.args[0]
    assert isinstance(enqueued_event, AgentTeamIdleEvent)


@pytest.mark.asyncio
async def test_dispatch_handler_exception_enqueues_error(agent_team_context):
    handler = MagicMock()
    handler.handle = AsyncMock(side_effect=RuntimeError("boom"))
    registry = MagicMock()
    registry.get_handler.return_value = handler
    dispatcher = AgentTeamEventDispatcher(registry)

    event = BaseAgentTeamEvent()
    await dispatcher.dispatch(event, agent_team_context)

    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_team_context.state.input_event_queues.enqueue_internal_system_event.call_args.args[0]
    assert isinstance(enqueued_event, AgentTeamErrorEvent)
