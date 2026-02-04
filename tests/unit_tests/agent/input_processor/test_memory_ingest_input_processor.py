import pytest
from unittest.mock import MagicMock, ANY

from autobyteus.agent.input_processor.memory_ingest_input_processor import MemoryIngestInputProcessor
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.sender_type import SenderType
from autobyteus.memory.memory_manager import MemoryManager


@pytest.mark.asyncio
async def test_memory_ingest_input_processor_sets_turn_id(agent_context):
    processor = MemoryIngestInputProcessor()
    memory_manager = MagicMock(spec=MemoryManager)
    memory_manager.start_turn.return_value = "turn_0001"
    agent_context.state.memory_manager = memory_manager

    message = AgentInputUserMessage(content="Hello")
    result = await processor.process(message, agent_context, triggering_event=MagicMock())

    assert result == message
    assert agent_context.state.active_turn_id == "turn_0001"
    memory_manager.ingest_user_message.assert_called_once_with(ANY, turn_id="turn_0001", source_event="LLMUserMessageReadyEvent")


@pytest.mark.asyncio
async def test_memory_ingest_input_processor_no_manager(agent_context):
    processor = MemoryIngestInputProcessor()
    agent_context.state.memory_manager = None

    message = AgentInputUserMessage(content="Hello")
    result = await processor.process(message, agent_context, triggering_event=MagicMock())

    assert result == message


@pytest.mark.asyncio
async def test_memory_ingest_input_processor_skips_tool_messages(agent_context):
    processor = MemoryIngestInputProcessor()
    memory_manager = MagicMock(spec=MemoryManager)
    agent_context.state.memory_manager = memory_manager
    agent_context.state.active_turn_id = "turn_existing"

    message = AgentInputUserMessage(content="Tool result", sender_type=SenderType.TOOL)
    result = await processor.process(message, agent_context, triggering_event=MagicMock())

    assert result == message
    assert agent_context.state.active_turn_id == "turn_existing"
    memory_manager.start_turn.assert_not_called()
    memory_manager.ingest_user_message.assert_not_called()
