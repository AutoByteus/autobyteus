import pytest
from unittest.mock import MagicMock

from autobyteus.agent.bootstrap_steps.working_context_snapshot_restore_step import WorkingContextSnapshotRestoreStep
from autobyteus.memory.restore.working_context_snapshot_bootstrapper import WorkingContextSnapshotBootstrapOptions


@pytest.mark.asyncio
async def test_working_context_snapshot_restore_step_noop_without_restore_options(agent_context):
    step = WorkingContextSnapshotRestoreStep()
    agent_context.state.restore_options = None

    result = await step.execute(agent_context)

    assert result is True


@pytest.mark.asyncio
async def test_working_context_snapshot_restore_step_calls_bootstrapper(agent_context):
    bootstrapper = MagicMock()
    step = WorkingContextSnapshotRestoreStep(bootstrapper=bootstrapper)
    agent_context.state.restore_options = WorkingContextSnapshotBootstrapOptions()
    agent_context.state.memory_manager = MagicMock()
    agent_context.state.processed_system_prompt = "System"

    result = await step.execute(agent_context)

    assert result is True
    bootstrapper.bootstrap.assert_called_once_with(
        agent_context.state.memory_manager,
        "System",
        agent_context.state.restore_options,
    )
