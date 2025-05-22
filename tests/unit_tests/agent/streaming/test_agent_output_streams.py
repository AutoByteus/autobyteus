# file: autobyteus/tests/unit_tests/agent/streaming/test_agent_output_streams.py
import asyncio
import pytest
from typing import List, Any, AsyncIterator, Dict, Optional
from unittest.mock import patch, AsyncMock

from autobyteus.agent.events import AgentEventQueues, END_OF_STREAM_SENTINEL
from autobyteus.agent.streaming.agent_output_streams import AgentOutputStreams
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def agent_event_queues() -> AgentEventQueues:
    """Fixture for a new AgentEventQueues instance."""
    return AgentEventQueues()

@pytest.fixture
def sentinel() -> object:
    """Fixture for the END_OF_STREAM_SENTINEL."""
    return END_OF_STREAM_SENTINEL

@pytest.fixture
def agent_id_fixture() -> str:
    """Fixture for a sample agent ID."""
    return "test_agent_001"

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

# Tests for individual stream methods
async def test_stream_assistant_output_chunks_normal(agent_event_queues: AgentEventQueues, sentinel: object):
    aos = AgentOutputStreams(agent_event_queues)
    items = ["chunk1 ", "chunk2 ", "chunk3"]
    await _put_items_and_sentinel(agent_event_queues.assistant_output_chunk_queue, items, sentinel)
    
    results = await _collect_stream_results(aos.stream_assistant_output_chunks())
    assert results == items

async def test_stream_assistant_output_chunks_empty(agent_event_queues: AgentEventQueues, sentinel: object):
    aos = AgentOutputStreams(agent_event_queues)
    await _put_items_and_sentinel(agent_event_queues.assistant_output_chunk_queue, [], sentinel)
    
    results = await _collect_stream_results(aos.stream_assistant_output_chunks())
    assert results == []

async def test_stream_assistant_final_messages_normal(agent_event_queues: AgentEventQueues, sentinel: object):
    aos = AgentOutputStreams(agent_event_queues)
    items = ["final message 1", "final message 2"]
    await _put_items_and_sentinel(agent_event_queues.assistant_final_message_queue, items, sentinel)
    
    results = await _collect_stream_results(aos.stream_assistant_final_messages())
    assert results == items

async def test_stream_tool_interaction_logs_normal(agent_event_queues: AgentEventQueues, sentinel: object):
    aos = AgentOutputStreams(agent_event_queues)
    items = ["log line 1", "log line 2", "log line 3"]
    await _put_items_and_sentinel(agent_event_queues.tool_interaction_log_queue, items, sentinel)
    
    results = await _collect_stream_results(aos.stream_tool_interaction_logs())
    assert results == items

# Tests for stream_unified_agent_events
async def test_unified_stream_single_source_chunks(agent_event_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    aos = AgentOutputStreams(agent_event_queues, agent_id=agent_id_fixture)
    chunk_items = ["c1", "c2"]
    
    # Populate only chunk queue
    await _put_items_and_sentinel(agent_event_queues.assistant_output_chunk_queue, chunk_items, sentinel)
    await _put_items_and_sentinel(agent_event_queues.assistant_final_message_queue, [], sentinel)
    await _put_items_and_sentinel(agent_event_queues.tool_interaction_log_queue, [], sentinel)

    results = await _collect_stream_results(aos.stream_unified_agent_events())
    
    assert len(results) == 2
    for i, item_str in enumerate(chunk_items):
        event = results[i]
        assert isinstance(event, StreamEvent)
        assert event.agent_id == agent_id_fixture
        assert event.event_type == StreamEventType.ASSISTANT_CHUNK
        assert event.data == {"chunk": item_str}

async def test_unified_stream_no_agent_id(agent_event_queues: AgentEventQueues, sentinel: object):
    aos = AgentOutputStreams(agent_event_queues) # No agent_id provided
    chunk_items = ["c1"]
    await _put_items_and_sentinel(agent_event_queues.assistant_output_chunk_queue, chunk_items, sentinel)
    await _put_items_and_sentinel(agent_event_queues.assistant_final_message_queue, [], sentinel)
    await _put_items_and_sentinel(agent_event_queues.tool_interaction_log_queue, [], sentinel)

    results = await _collect_stream_results(aos.stream_unified_agent_events())
    assert len(results) == 1
    assert results[0].agent_id is None

async def test_unified_stream_multiple_sources(agent_event_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    aos = AgentOutputStreams(agent_event_queues, agent_id=agent_id_fixture)
    
    chunk_items = ["chunkA", "chunkB"]
    final_msg_items = ["finalMsg1"]
    log_items = ["toolLogX", "toolLogY", "toolLogZ"]

    await _put_items_and_sentinel(agent_event_queues.assistant_output_chunk_queue, chunk_items, sentinel)
    await _put_items_and_sentinel(agent_event_queues.assistant_final_message_queue, final_msg_items, sentinel)
    await _put_items_and_sentinel(agent_event_queues.tool_interaction_log_queue, log_items, sentinel)

    results = await _collect_stream_results(aos.stream_unified_agent_events())
    
    assert len(results) == len(chunk_items) + len(final_msg_items) + len(log_items)

    # Verify counts and content (order is not guaranteed)
    received_chunks = [e.data["chunk"] for e in results if e.event_type == StreamEventType.ASSISTANT_CHUNK]
    received_final_msgs = [e.data["message"] for e in results if e.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE]
    received_logs = [e.data["log_line"] for e in results if e.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY]

    assert sorted(received_chunks) == sorted(chunk_items)
    assert sorted(received_final_msgs) == sorted(final_msg_items)
    assert sorted(received_logs) == sorted(log_items)

    for event in results:
        assert event.agent_id == agent_id_fixture

async def test_unified_stream_empty_sources(agent_event_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    aos = AgentOutputStreams(agent_event_queues, agent_id=agent_id_fixture)

    await _put_items_and_sentinel(agent_event_queues.assistant_output_chunk_queue, [], sentinel)
    await _put_items_and_sentinel(agent_event_queues.assistant_final_message_queue, [], sentinel)
    await _put_items_and_sentinel(agent_event_queues.tool_interaction_log_queue, [], sentinel)

    results = await _collect_stream_results(aos.stream_unified_agent_events())
    assert len(results) == 0

async def test_unified_stream_cancellation(agent_event_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    aos = AgentOutputStreams(agent_event_queues, agent_id=agent_id_fixture)
    
    # Add items to one queue to ensure the stream starts processing
    await agent_event_queues.assistant_output_chunk_queue.put("chunk1")
    # Do not add sentinel yet to one of the queues, or make them slow
    # Here, we just test basic cancellation propagation

    unified_stream_gen = aos.stream_unified_agent_events()
    
    task = asyncio.create_task(_collect_stream_results(unified_stream_gen))

    await asyncio.sleep(0.01) # Let it start
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    
    # Ensure any pending futures within AgentOutputStreams are also cancelled
    # This is handled internally by AgentOutputStreams's finally block in stream_unified_agent_events

async def test_unified_stream_error_in_source_stream(agent_event_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    aos = AgentOutputStreams(agent_event_queues, agent_id=agent_id_fixture)

    # Mock one of the underlying string stream methods to raise an exception
    error_message = "Simulated stream error"
    
    async def faulty_chunk_stream():
        yield "good_chunk"
        raise ValueError(error_message)
        yield "never_reached_chunk" # pylint: disable=unreachable

    # Put sentinels in other queues so they complete normally
    await _put_items_and_sentinel(agent_event_queues.assistant_final_message_queue, ["final"], sentinel)
    await _put_items_and_sentinel(agent_event_queues.tool_interaction_log_queue, ["log"], sentinel)
    
    # Patch the instance's method directly
    with patch.object(aos, 'stream_assistant_output_chunks', side_effect=faulty_chunk_stream) as mock_faulty_stream:
        results = await _collect_stream_results(aos.stream_unified_agent_events())

    mock_faulty_stream.assert_called_once()

    # Expected: one good chunk, one final message, one log, one error event
    assert len(results) == 4 # good_chunk, final, log, error_event
    
    error_events = [e for e in results if e.event_type == StreamEventType.ERROR_EVENT]
    assert len(error_events) == 1
    error_event = error_events[0]
    assert error_event.agent_id == agent_id_fixture
    assert error_event.data["error"] == error_message
    assert error_event.data["source_stream"] == "assistant_chunks" # Check the source description
    assert "ValueError" in error_event.data["details"]

    # Check other events
    good_chunk_events = [e for e in results if e.event_type == StreamEventType.ASSISTANT_CHUNK and e.data["chunk"] == "good_chunk"]
    assert len(good_chunk_events) == 1

    final_events = [e for e in results if e.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE and e.data["message"] == "final"]
    assert len(final_events) == 1

    log_events = [e for e in results if e.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY and e.data["log_line"] == "log"]
    assert len(log_events) == 1


async def test_unified_stream_handles_mixed_completion_and_errors(agent_event_queues: AgentEventQueues, sentinel: object, agent_id_fixture: str):
    aos = AgentOutputStreams(agent_event_queues, agent_id=agent_id_fixture)

    # Chunks stream will be normal
    chunk_items = ["c1", "c2"]
    await _put_items_and_sentinel(agent_event_queues.assistant_output_chunk_queue, chunk_items, sentinel)

    # Final message stream will have an error
    final_msg_error = "Final message stream blew up"
    async def faulty_final_msg_stream():
        yield "good_final_msg_part"
        raise RuntimeError(final_msg_error)

    # Tool log stream will also be normal
    log_items = ["logA"]
    await _put_items_and_sentinel(agent_event_queues.tool_interaction_log_queue, log_items, sentinel)

    with patch.object(aos, 'stream_assistant_final_messages', side_effect=faulty_final_msg_stream):
        results = await _collect_stream_results(aos.stream_unified_agent_events())

    # Expected: c1, c2, good_final_msg_part, error_event_for_final, logA
    # Total 5 events
    assert len(results) == 5

    event_types_counts = {}
    for event in results:
        event_types_counts[event.event_type] = event_types_counts.get(event.event_type, 0) + 1
        if event.event_type == StreamEventType.ERROR_EVENT:
            assert event.data["error"] == final_msg_error
            assert event.data["source_stream"] == "assistant_final_messages"
        if event.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE:
            assert event.data["message"] == "good_final_msg_part"


    assert event_types_counts.get(StreamEventType.ASSISTANT_CHUNK) == 2
    assert event_types_counts.get(StreamEventType.ASSISTANT_FINAL_MESSAGE) == 1 # The "good" part before error
    assert event_types_counts.get(StreamEventType.TOOL_INTERACTION_LOG_ENTRY) == 1
    assert event_types_counts.get(StreamEventType.ERROR_EVENT) == 1

