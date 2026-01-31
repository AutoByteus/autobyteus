import pytest
from unittest.mock import MagicMock

from autobyteus.agent.tool_execution_result_processor.memory_ingest_tool_result_processor import (
    MemoryIngestToolResultProcessor,
)
from autobyteus.agent.events.agent_events import ToolResultEvent
from autobyteus.memory.memory_manager import MemoryManager


@pytest.mark.asyncio
async def test_memory_ingest_tool_result_processor(agent_context):
    processor = MemoryIngestToolResultProcessor()
    memory_manager = MagicMock(spec=MemoryManager)
    agent_context.state.memory_manager = memory_manager

    event = ToolResultEvent(tool_name="tool", result="ok", tool_invocation_id="call_1", turn_id="turn_0001")
    result = await processor.process(event, agent_context)

    assert result == event
    memory_manager.ingest_tool_result.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_memory_ingest_tool_result_processor_no_manager(agent_context):
    processor = MemoryIngestToolResultProcessor()
    agent_context.state.memory_manager = None

    event = ToolResultEvent(tool_name="tool", result="ok", tool_invocation_id="call_1", turn_id="turn_0001")
    result = await processor.process(event, agent_context)

    assert result == event


@pytest.mark.asyncio
async def test_memory_ingest_tool_result_processor_missing_turn_id(agent_context):
    processor = MemoryIngestToolResultProcessor()
    memory_manager = MagicMock(spec=MemoryManager)
    agent_context.state.memory_manager = memory_manager

    event = ToolResultEvent(tool_name="tool", result="ok", tool_invocation_id="call_1", turn_id=None)
    result = await processor.process(event, agent_context)

    assert result == event
    memory_manager.ingest_tool_result.assert_not_called()
