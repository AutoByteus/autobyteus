# file: autobyteus/tests/unit_tests/agent_team/status/test_status_update_utils.py
import pytest
from unittest.mock import AsyncMock

from autobyteus.agent_team.status.status_update_utils import apply_event_and_derive_status
from autobyteus.agent_team.status.status_deriver import AgentTeamStatusDeriver
from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus
from autobyteus.agent_team.events.event_store import AgentTeamEventStore
from autobyteus.agent_team.events.agent_team_events import (
    AgentTeamBootstrapStartedEvent,
    AgentTeamErrorEvent,
    ProcessUserMessageEvent,
)
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage


@pytest.mark.asyncio
async def test_apply_event_updates_status_and_store(agent_team_context):
    agent_team_context.state.status_deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.UNINITIALIZED)
    agent_team_context.state.event_store = AgentTeamEventStore(team_id=agent_team_context.team_id)
    agent_team_context.state.current_status = AgentTeamStatus.UNINITIALIZED
    agent_team_context.status_manager.emit_status_update = AsyncMock()

    old_status, new_status = await apply_event_and_derive_status(
        AgentTeamBootstrapStartedEvent(), agent_team_context
    )

    assert old_status == AgentTeamStatus.UNINITIALIZED
    assert new_status == AgentTeamStatus.BOOTSTRAPPING
    assert agent_team_context.current_status == AgentTeamStatus.BOOTSTRAPPING
    agent_team_context.status_manager.emit_status_update.assert_awaited_once()
    assert len(agent_team_context.state.event_store.all_events()) == 1


@pytest.mark.asyncio
async def test_apply_event_includes_error_payload(agent_team_context):
    agent_team_context.state.status_deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.IDLE)
    agent_team_context.state.event_store = AgentTeamEventStore(team_id=agent_team_context.team_id)
    agent_team_context.state.current_status = AgentTeamStatus.IDLE
    agent_team_context.status_manager.emit_status_update = AsyncMock()

    await apply_event_and_derive_status(
        AgentTeamErrorEvent(error_message="boom", exception_details="trace"),
        agent_team_context
    )

    call_kwargs = agent_team_context.status_manager.emit_status_update.call_args.kwargs
    assert call_kwargs["additional_data"] == {"error_message": "boom"}


@pytest.mark.asyncio
async def test_operational_event_sets_processing(agent_team_context):
    agent_team_context.state.status_deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.IDLE)
    agent_team_context.state.event_store = AgentTeamEventStore(team_id=agent_team_context.team_id)
    agent_team_context.state.current_status = AgentTeamStatus.IDLE
    agent_team_context.status_manager.emit_status_update = AsyncMock()

    event = ProcessUserMessageEvent(
        user_message=AgentInputUserMessage(content="hi"),
        target_agent_name="Coordinator",
    )

    old_status, new_status = await apply_event_and_derive_status(event, agent_team_context)
    assert old_status == AgentTeamStatus.IDLE
    assert new_status == AgentTeamStatus.PROCESSING
