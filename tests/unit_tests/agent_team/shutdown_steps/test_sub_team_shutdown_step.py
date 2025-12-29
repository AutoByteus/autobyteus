# file: autobyteus/tests/unit_tests/agent_team/shutdown_steps/test_sub_team_shutdown_step.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent_team.shutdown_steps.sub_team_shutdown_step import SubTeamShutdownStep


@pytest.mark.asyncio
async def test_execute_no_team_manager(agent_team_context):
    agent_team_context.state.team_manager = None
    step = SubTeamShutdownStep()

    success = await step.execute(agent_team_context)

    assert success is True


@pytest.mark.asyncio
async def test_execute_no_running_sub_teams(agent_team_context):
    team_manager = MagicMock()
    team_manager.get_all_sub_teams.return_value = []
    agent_team_context.state.team_manager = team_manager
    step = SubTeamShutdownStep()

    success = await step.execute(agent_team_context)

    assert success is True
    team_manager.get_all_sub_teams.assert_called_once()


@pytest.mark.asyncio
async def test_execute_stops_running_sub_teams(agent_team_context):
    running_team = MagicMock()
    running_team.name = "Sub1"
    running_team.is_running = True
    running_team.stop = AsyncMock(return_value=None)

    stopped_team = MagicMock()
    stopped_team.name = "Sub2"
    stopped_team.is_running = False

    team_manager = MagicMock()
    team_manager.get_all_sub_teams.return_value = [running_team, stopped_team]
    agent_team_context.state.team_manager = team_manager
    step = SubTeamShutdownStep()

    success = await step.execute(agent_team_context)

    assert success is True
    running_team.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_reports_failure_on_exception(agent_team_context):
    failing_team = MagicMock()
    failing_team.name = "Failing"
    failing_team.is_running = True
    failing_team.stop = AsyncMock(side_effect=RuntimeError("boom"))

    team_manager = MagicMock()
    team_manager.get_all_sub_teams.return_value = [failing_team]
    agent_team_context.state.team_manager = team_manager
    step = SubTeamShutdownStep()

    success = await step.execute(agent_team_context)

    assert success is False
