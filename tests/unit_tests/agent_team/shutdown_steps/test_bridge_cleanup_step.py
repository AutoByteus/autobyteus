# file: autobyteus/tests/unit_tests/agent_team/shutdown_steps/test_bridge_cleanup_step.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.shutdown_steps.bridge_cleanup_step import BridgeCleanupStep


@pytest.mark.asyncio
async def test_execute_no_multiplexer(agent_team_context):
    agent_team_context.state.multiplexer_ref = None
    step = BridgeCleanupStep()

    with patch('autobyteus.agent_team.shutdown_steps.bridge_cleanup_step.logger') as mock_logger:
        success = await step.execute(agent_team_context)

    assert success is True
    mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_execute_shutdown_success(agent_team_context):
    multiplexer = MagicMock()
    multiplexer.shutdown = AsyncMock()
    agent_team_context.state.multiplexer_ref = multiplexer
    step = BridgeCleanupStep()

    success = await step.execute(agent_team_context)

    assert success is True
    multiplexer.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_shutdown_failure(agent_team_context):
    multiplexer = MagicMock()
    multiplexer.shutdown = AsyncMock(side_effect=RuntimeError("boom"))
    agent_team_context.state.multiplexer_ref = multiplexer
    step = BridgeCleanupStep()

    success = await step.execute(agent_team_context)

    assert success is False
