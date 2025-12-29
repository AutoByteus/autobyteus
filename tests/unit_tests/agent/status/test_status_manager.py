# file: autobyteus/tests/unit_tests/agent/status/test_status_manager.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.status.manager import AgentStatusManager
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.lifecycle import LifecycleEvent


@pytest.mark.asyncio
async def test_emit_status_update_no_change(agent_context):
    notifier = MagicMock()
    manager = AgentStatusManager(context=agent_context, notifier=notifier)

    processor = MagicMock()
    processor.event = LifecycleEvent.AGENT_READY
    processor.get_order.return_value = 100
    processor.get_name.return_value = "Processor"
    processor.process = AsyncMock()
    agent_context.config.lifecycle_processors = [processor]

    await manager.emit_status_update(AgentStatus.IDLE, AgentStatus.IDLE)

    processor.process.assert_not_awaited()
    notifier.notify_status_updated.assert_not_called()


@pytest.mark.asyncio
async def test_emit_status_update_runs_lifecycle_processors_in_order(agent_context):
    notifier = MagicMock()
    manager = AgentStatusManager(context=agent_context, notifier=notifier)

    call_order = []
    processor_late = MagicMock()
    processor_late.event = LifecycleEvent.AGENT_READY
    processor_late.get_order.return_value = 200
    processor_late.get_name.return_value = "Late"
    processor_late.process = AsyncMock(side_effect=lambda *args, **kwargs: call_order.append("late"))

    processor_early = MagicMock()
    processor_early.event = LifecycleEvent.AGENT_READY
    processor_early.get_order.return_value = 100
    processor_early.get_name.return_value = "Early"
    processor_early.process = AsyncMock(side_effect=lambda *args, **kwargs: call_order.append("early"))

    agent_context.config.lifecycle_processors = [processor_late, processor_early]

    await manager.emit_status_update(
        AgentStatus.BOOTSTRAPPING,
        AgentStatus.IDLE,
        additional_data={"foo": "bar"},
    )

    assert call_order == ["early", "late"]
    processor_early.process.assert_awaited_once_with(agent_context, {"foo": "bar"})
    processor_late.process.assert_awaited_once_with(agent_context, {"foo": "bar"})
    notifier.notify_status_updated.assert_called_once_with(
        AgentStatus.IDLE,
        AgentStatus.BOOTSTRAPPING,
        {"foo": "bar"},
    )


@pytest.mark.asyncio
async def test_emit_status_update_handles_processor_errors(agent_context):
    notifier = MagicMock()
    manager = AgentStatusManager(context=agent_context, notifier=notifier)

    processor = MagicMock()
    processor.event = LifecycleEvent.BEFORE_LLM_CALL
    processor.get_order.return_value = 100
    processor.get_name.return_value = "Fails"
    processor.process = AsyncMock(side_effect=RuntimeError("boom"))

    agent_context.config.lifecycle_processors = [processor]

    await manager.emit_status_update(
        AgentStatus.PROCESSING_USER_INPUT,
        AgentStatus.AWAITING_LLM_RESPONSE,
    )

    processor.process.assert_awaited_once()
    notifier.notify_status_updated.assert_called_once_with(
        AgentStatus.AWAITING_LLM_RESPONSE,
        AgentStatus.PROCESSING_USER_INPUT,
        None,
    )
