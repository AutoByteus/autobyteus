# file: autobyteus/tests/unit_tests/agent_team/status/test_status_deriver.py
from autobyteus.agent_team.status.status_deriver import AgentTeamStatusDeriver
from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus
from autobyteus.agent_team.events.agent_team_events import (
    AgentTeamBootstrapStartedEvent,
    AgentTeamReadyEvent,
    AgentTeamIdleEvent,
    AgentTeamShutdownRequestedEvent,
    AgentTeamStoppedEvent,
    AgentTeamErrorEvent,
    ProcessUserMessageEvent,
)
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage


def test_bootstrap_and_ready_transitions():
    deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.UNINITIALIZED)
    old_status, new_status = deriver.apply(AgentTeamBootstrapStartedEvent())
    assert old_status == AgentTeamStatus.UNINITIALIZED
    assert new_status == AgentTeamStatus.BOOTSTRAPPING

    old_status, new_status = deriver.apply(AgentTeamReadyEvent())
    assert old_status == AgentTeamStatus.BOOTSTRAPPING
    assert new_status == AgentTeamStatus.IDLE

    old_status, new_status = deriver.apply(AgentTeamIdleEvent())
    assert old_status == AgentTeamStatus.IDLE
    assert new_status == AgentTeamStatus.IDLE


def test_operational_transition_to_processing():
    deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.IDLE)
    event = ProcessUserMessageEvent(
        user_message=AgentInputUserMessage(content="hi"),
        target_agent_name="Coordinator",
    )
    old_status, new_status = deriver.apply(event)
    assert old_status == AgentTeamStatus.IDLE
    assert new_status == AgentTeamStatus.PROCESSING


def test_shutdown_and_error_transitions():
    deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.IDLE)
    old_status, new_status = deriver.apply(AgentTeamShutdownRequestedEvent())
    assert new_status == AgentTeamStatus.SHUTTING_DOWN

    deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.ERROR)
    old_status, new_status = deriver.apply(AgentTeamShutdownRequestedEvent())
    assert new_status == AgentTeamStatus.ERROR

    deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.IDLE)
    old_status, new_status = deriver.apply(AgentTeamStoppedEvent())
    assert new_status == AgentTeamStatus.SHUTDOWN_COMPLETE

    deriver = AgentTeamStatusDeriver(initial_status=AgentTeamStatus.ERROR)
    old_status, new_status = deriver.apply(AgentTeamStoppedEvent())
    assert new_status == AgentTeamStatus.ERROR

    old_status, new_status = deriver.apply(AgentTeamErrorEvent(error_message="boom"))
    assert new_status == AgentTeamStatus.ERROR
