# file: autobyteus/tests/unit_tests/agent_team/status/test_agent_team_status_manager.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.status.agent_team_status_manager import AgentTeamStatusManager
from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus


@pytest.mark.asyncio
async def test_status_manager_emits_update(agent_team_context):
    notifier = MagicMock()
    notifier.notify_status_updated = MagicMock()
    manager = AgentTeamStatusManager(context=agent_team_context, notifier=notifier)

    await manager.emit_status_update(AgentTeamStatus.UNINITIALIZED, AgentTeamStatus.BOOTSTRAPPING)
    notifier.notify_status_updated.assert_called_once_with(
        AgentTeamStatus.BOOTSTRAPPING,
        AgentTeamStatus.UNINITIALIZED,
        None,
    )


@pytest.mark.asyncio
async def test_status_manager_does_not_notify_on_same_status(agent_team_context):
    notifier = MagicMock()
    notifier.notify_status_updated = MagicMock()
    manager = AgentTeamStatusManager(context=agent_team_context, notifier=notifier)

    await manager.emit_status_update(AgentTeamStatus.IDLE, AgentTeamStatus.IDLE)

    notifier.notify_status_updated.assert_not_called()


@pytest.mark.asyncio
async def test_status_manager_passes_additional_payload(agent_team_context):
    notifier = MagicMock()
    notifier.notify_status_updated = MagicMock()
    manager = AgentTeamStatusManager(context=agent_team_context, notifier=notifier)

    await manager.emit_status_update(
        AgentTeamStatus.IDLE,
        AgentTeamStatus.ERROR,
        additional_data={"error_message": "boom"},
    )

    notifier.notify_status_updated.assert_called_once_with(
        AgentTeamStatus.ERROR,
        AgentTeamStatus.IDLE,
        {"error_message": "boom"},
    )


def test_status_manager_requires_notifier(agent_team_context):
    with pytest.raises(ValueError):
        AgentTeamStatusManager(context=agent_team_context, notifier=None)
