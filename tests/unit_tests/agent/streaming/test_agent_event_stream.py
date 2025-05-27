# file: autobyteus/tests/unit_tests/agent/streaming/test_agent_event_stream.py
import asyncio
import pytest
from typing import List, Any, AsyncIterator, Dict, Optional
from unittest.mock import MagicMock, patch, AsyncMock # Added MagicMock

from autobyteus.agent.events import AgentEventQueues, END_OF_STREAM_SENTINEL
# MODIFIED: Import AgentEventStream instead of AgentOutputStreams
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse # For type checking items
from autobyteus.agent.agent import Agent # IMPORT ADDED for spec

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_agent_queues() -> AgentEventQueues:
    """Fixture for a new AgentEventQueues instance for the mock agent."""
    return AgentEventQueues()

@pytest.fixture
def sentinel() -> object:
    """Fixture for the END_OF_STREAM_SENTINEL."""
    return END_OF_STREAM_SENTINEL

@pytest.fixture
def agent_id_fixture() -> str:
    """Fixture for a sample agent ID."""
    return "test_agent_001"

@pytest.fixture
def mock_agent(agent_id_fixture: str, mock_agent_queues: AgentEventQueues) -> MagicMock:
    """Fixture for a mock Agent instance."""
    # MODIFIED: Use spec=Agent to make the mock pass isinstance checks
    agent = MagicMock(spec=Agent) 
    agent.agent_id = agent_id_fixture
    agent.get_event_queues = MagicMock(return_value=mock_agent_queues)
    # If AgentEventStream's __init__ were to access agent.context, it would need to be mocked too:
    # agent.context = MagicMock() 
    # agent.context.agent_id = agent_id_fixture # if agent_id was sourced from context for example
    return agent

@pytest.fixture
def streamer(mock_agent: MagicMock) -> AgentEventStream:
    """Fixture for an AgentEventStream instance initialized with a mock agent."""
    return AgentEventStream(mock_agent)

async def _collect_stream_results(stream: AsyncIterator[Any]) -> List[Any]:
    """Helper function to collect all items from an async iterator into a list."""
    results = []
    async for item in stream:
        results.append(item)
    return results

async def _put_items_and_sentinel(queue: asyncio.Queue, items: List[Any], sentinel_obj: object):
    """Helper to put items and then a sentinel into a queue."""
    for item in items:
        await queue.put(item)
    await queue.put(sentinel_obj)

# Tests for individual raw stream methods
async def test_stream_assistant_chunks_normal(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object):
    # Items are now ChunkResponse objects
    items = [ChunkResponse(content="chunk1 "), ChunkResponse(content="chunk2 "), ChunkResponse(content="chunk3 ")]
    await _put_items_and_sentinel(mock_agent_queues.assistant_output_chunk_queue, items, sentinel)
    
    # MODIFIED: Call the new method
    results = await _collect_stream_results(streamer.stream_assistant_chunks())
    # Compare based on content if desired, or full objects
    assert [r.content for r in results] == [i.content for i in items]

async def test_stream_assistant_chunks_empty(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object):
    await _put_items_and_sentinel(mock_agent_queues.assistant_output_chunk_queue, [], sentinel)
    
    results = await _collect_stream_results(streamer.stream_assistant_chunks())
    assert results == []

async def test_stream_assistant_final_messages_normal(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object):
    # Items are CompleteResponse objects
    items = [CompleteResponse(content="final message 1"), CompleteResponse(content="final message 2")]
    await _put_items_and_sentinel(mock_agent_queues.assistant_final_message_queue, items, sentinel)
    
    results = await _collect_stream_results(streamer.stream_assistant_final_messages())
    assert [r.content for r in results] == [i.content for i in items]

async def test_stream_tool_logs_normal(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object):
    items = ["log line 1", "log line 2", "log line 3"]
    await _put_items_and_sentinel(mock_agent_queues.tool_interaction_log_queue, items, sentinel)
    
    results = await _collect_stream_results(streamer.stream_tool_logs())
    assert results == items

# Tests for all_events (previously stream_unified_agent_events)
async def test_all_events_single_source_chunks(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    # Items for raw stream are ChunkResponse
    chunk_items_raw = [ChunkResponse(content="c1"), ChunkResponse(content="c2")]
    
    await _put_items_and_sentinel(mock_agent_queues.assistant_output_chunk_queue, chunk_items_raw, sentinel)
    await _put_items_and_sentinel(mock_agent_queues.assistant_final_message_queue, [], sentinel)
    await _put_items_and_sentinel(mock_agent_queues.tool_interaction_log_queue, [], sentinel)

    # MODIFIED: Call the new method
    results = await _collect_stream_results(streamer.all_events())
    
    assert len(results) == 2
    for i, raw_chunk in enumerate(chunk_items_raw):
        event = results[i]
        assert isinstance(event, StreamEvent)
        assert event.agent_id == agent_id_fixture # streamer gets agent_id from mock_agent
        assert event.event_type == StreamEventType.ASSISTANT_CHUNK
        assert event.data.get("chunk") == raw_chunk.content

async def test_all_events_agent_id_propagation(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    # This test now verifies agent_id propagation from the mock_agent
    chunk_items_raw = [ChunkResponse(content="c1")]
    await _put_items_and_sentinel(mock_agent_queues.assistant_output_chunk_queue, chunk_items_raw, sentinel)
    await _put_items_and_sentinel(mock_agent_queues.assistant_final_message_queue, [], sentinel)
    await _put_items_and_sentinel(mock_agent_queues.tool_interaction_log_queue, [], sentinel)

    results = await _collect_stream_results(streamer.all_events())
    assert len(results) == 1
    assert results[0].agent_id == agent_id_fixture # Check against the fixture ID

async def test_all_events_multiple_sources(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    chunk_items_raw = [ChunkResponse(content="chunkA"), ChunkResponse(content="chunkB")]
    final_msg_items_raw = [CompleteResponse(content="finalMsg1")]
    log_items_raw = ["toolLogX", "toolLogY", "toolLogZ"]

    await _put_items_and_sentinel(mock_agent_queues.assistant_output_chunk_queue, chunk_items_raw, sentinel)
    await _put_items_and_sentinel(mock_agent_queues.assistant_final_message_queue, final_msg_items_raw, sentinel)
    await _put_items_and_sentinel(mock_agent_queues.tool_interaction_log_queue, log_items_raw, sentinel)

    results = await _collect_stream_results(streamer.all_events())
    
    assert len(results) == len(chunk_items_raw) + len(final_msg_items_raw) + len(log_items_raw)

    received_chunks_content = [e.data["chunk"] for e in results if e.event_type == StreamEventType.ASSISTANT_CHUNK]
    received_final_msgs_content = [e.data["message"] for e in results if e.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE]
    received_logs = [e.data["log_line"] for e in results if e.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY]

    assert sorted(received_chunks_content) == sorted([c.content for c in chunk_items_raw])
    assert sorted(received_final_msgs_content) == sorted([m.content for m in final_msg_items_raw])
    assert sorted(received_logs) == sorted(log_items_raw)

    for event in results:
        assert event.agent_id == agent_id_fixture

async def test_all_events_empty_sources(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object):
    await _put_items_and_sentinel(mock_agent_queues.assistant_output_chunk_queue, [], sentinel)
    await _put_items_and_sentinel(mock_agent_queues.assistant_final_message_queue, [], sentinel)
    await _put_items_and_sentinel(mock_agent_queues.tool_interaction_log_queue, [], sentinel)

    results = await _collect_stream_results(streamer.all_events())
    assert len(results) == 0

async def test_all_events_cancellation(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues): # sentinel not strictly needed for this test
    await mock_agent_queues.assistant_output_chunk_queue.put(ChunkResponse(content="chunk1"))
    
    unified_stream_gen = streamer.all_events()
    task = asyncio.create_task(_collect_stream_results(unified_stream_gen))
    await asyncio.sleep(0.01) 
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    
async def test_all_events_error_in_source_stream(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    error_message = "Simulated stream error"
    
    async def faulty_chunk_stream():
        yield ChunkResponse(content="good_chunk")
        raise ValueError(error_message)
        # yield ChunkResponse(content="never_reached_chunk") # pylint: disable=unreachable

    await _put_items_and_sentinel(mock_agent_queues.assistant_final_message_queue, [CompleteResponse(content="final")], sentinel)
    await _put_items_and_sentinel(mock_agent_queues.tool_interaction_log_queue, ["log"], sentinel)
    
    # Patch the instance's direct raw stream method
    with patch.object(streamer, 'stream_assistant_chunks', side_effect=faulty_chunk_stream) as mock_faulty_method:
        results = await _collect_stream_results(streamer.all_events())

    mock_faulty_method.assert_called_once()

    assert len(results) == 4 
    
    error_events = [e for e in results if e.event_type == StreamEventType.ERROR_EVENT]
    assert len(error_events) == 1
    error_event = error_events[0]
    assert error_event.agent_id == agent_id_fixture
    assert error_event.data["error"] == error_message
    # MODIFIED: The source_stream key from iterators_map is "assistant_chunks"
    assert error_event.data["source_stream"] == "assistant_chunks" 
    assert "ValueError" in error_event.data["details"]

    good_chunk_events = [e for e in results if e.event_type == StreamEventType.ASSISTANT_CHUNK and e.data["chunk"] == "good_chunk"]
    assert len(good_chunk_events) == 1
    final_events = [e for e in results if e.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE and e.data["message"] == "final"]
    assert len(final_events) == 1
    log_events = [e for e in results if e.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY and e.data["log_line"] == "log"]
    assert len(log_events) == 1

async def test_all_events_handles_mixed_completion_and_errors(streamer: AgentEventStream, mock_agent_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    chunk_items_raw = [ChunkResponse(content="c1"), ChunkResponse(content="c2")]
    await _put_items_and_sentinel(mock_agent_queues.assistant_output_chunk_queue, chunk_items_raw, sentinel)

    final_msg_error = "Final message stream blew up"
    async def faulty_final_msg_stream():
        yield CompleteResponse(content="good_final_msg_part")
        raise RuntimeError(final_msg_error)

    log_items_raw = ["logA"]
    await _put_items_and_sentinel(mock_agent_queues.tool_interaction_log_queue, log_items_raw, sentinel)

    with patch.object(streamer, 'stream_assistant_final_messages', side_effect=faulty_final_msg_stream):
        results = await _collect_stream_results(streamer.all_events())

    assert len(results) == 5

    event_types_counts = {}
    for event in results:
        event_types_counts[event.event_type] = event_types_counts.get(event.event_type, 0) + 1
        if event.event_type == StreamEventType.ERROR_EVENT:
            assert event.data["error"] == final_msg_error
            # MODIFIED: The source_stream key from iterators_map is "assistant_final_messages"
            assert event.data["source_stream"] == "assistant_final_messages"
        if event.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE:
            assert event.data["message"] == "good_final_msg_part"

    assert event_types_counts.get(StreamEventType.ASSISTANT_CHUNK) == 2
    assert event_types_counts.get(StreamEventType.ASSISTANT_FINAL_MESSAGE) == 1
    assert event_types_counts.get(StreamEventType.TOOL_INTERACTION_LOG_ENTRY) == 1
    assert event_types_counts.get(StreamEventType.ERROR_EVENT) == 1
