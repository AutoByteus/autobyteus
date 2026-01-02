# file: autobyteus/tests/unit_tests/agent/streaming/test_agent_event_stream.py
import asyncio
import pytest
import pytest_asyncio
import threading
from typing import List, Any, AsyncIterator, Coroutine, Generator
from unittest.mock import MagicMock

from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType, AgentStatusUpdateData
from autobyteus.agent.streaming.stream_event_payloads import AssistantChunkData, AssistantCompleteResponseData, ErrorEventData
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.agent.agent import Agent
from autobyteus.agent.status.manager import AgentStatusManager
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier
from autobyteus.agent.status.status_enum import AgentStatus

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# --- Test Helpers ---

def run_producer_in_thread(producer_coro: Coroutine) -> threading.Thread:
    """
    Runs a coroutine in a new thread with its own dedicated event loop.
    This simulates the agent worker thread producing events.
    """
    def thread_target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(producer_coro)
        finally:
            # Cleanly shut down all tasks in the new loop before closing it.
            tasks = asyncio.all_tasks(loop=loop)
            if tasks:
                async def gather_cancelled():
                    await asyncio.gather(*tasks, return_exceptions=True)
                for task in tasks:
                    task.cancel()
                loop.run_until_complete(gather_cancelled())
            loop.close()
            
    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()
    return thread

async def _collect_stream_results(stream: AsyncIterator[Any], timeout: float = 1.0) -> List[Any]:
    """Helper function to collect all items from an async iterator into a list."""
    results = []
    try:
        async def _collect():
            async for item in stream:
                results.append(item)
        await asyncio.wait_for(_collect(), timeout=timeout)
    except asyncio.TimeoutError:
        pass # Expected timeout when stream is done or producer finishes
    return results

# --- Pytest Fixtures ---

@pytest.fixture
def agent_id_fixture() -> str:
    """Fixture for a sample agent ID."""
    return "stream_test_agent_001"

@pytest.fixture
def real_notifier(agent_id_fixture: str) -> AgentExternalEventNotifier:
    """Fixture for a real AgentExternalEventNotifier instance."""
    return AgentExternalEventNotifier(agent_id=agent_id_fixture)

@pytest.fixture
def mock_agent(agent_id_fixture: str, real_notifier: AgentExternalEventNotifier) -> MagicMock:
    """
    Fixture for a mock Agent instance that is correctly configured for the streamer.
    The streamer's __init__ accesses agent.context.status_manager.notifier.
    """
    mock_agent_context = MagicMock(spec=AgentContext)
    mock_agent_context.agent_id = agent_id_fixture
    
    mock_status_manager = MagicMock(spec=AgentStatusManager)
    mock_status_manager.notifier = real_notifier
    mock_agent_context.status_manager = mock_status_manager
    
    agent = MagicMock(spec=Agent)
    agent.agent_id = agent_id_fixture
    agent.context = mock_agent_context
    return agent

@pytest_asyncio.fixture
async def streamer(mock_agent: MagicMock) -> Generator[AgentEventStream, None, None]:
    """
    Fixture for an AgentEventStream instance. Yields the streamer and handles async cleanup.
    """
    s = AgentEventStream(mock_agent)
    yield s
    await s.close()

# --- Test Cases ---

async def test_stream_assistant_chunks(streamer: AgentEventStream, real_notifier: AgentExternalEventNotifier):
    """Tests that chunks are correctly streamed across threads."""
    chunk1 = ChunkResponse(content="Hello ")
    chunk2 = ChunkResponse(content="World")
    
    # This producer coroutine will run in a separate thread.
    async def produce_events():
        await asyncio.sleep(0.05) # Give consumer time to start awaiting.
        real_notifier.notify_agent_data_assistant_chunk(chunk1)
        real_notifier.notify_agent_data_assistant_chunk(chunk2)
        # No stream-end event needed; chunk stream closes naturally.

    # Consumer runs in the main test event loop.
    consumer_task = asyncio.create_task(
        _collect_stream_results(streamer.stream_assistant_chunks())
    )
    
    # Start the producer in its own thread.
    producer_thread = run_producer_in_thread(produce_events())
    
    results = await consumer_task
    producer_thread.join(timeout=1.0)
    
    assert [r.content for r in results] == ["Hello ", "World"]

async def test_stream_assistant_final_messages(streamer: AgentEventStream, real_notifier: AgentExternalEventNotifier):
    """Tests that the final complete response is streamed correctly across threads."""
    final_msg = CompleteResponse(content="This is the final message.")
    
    async def produce_events():
        await asyncio.sleep(0.05)
        real_notifier.notify_agent_data_assistant_complete_response(final_msg)

    consumer_task = asyncio.create_task(
        _collect_stream_results(streamer.stream_assistant_final_response())
    )
    
    producer_thread = run_producer_in_thread(produce_events())
    results = await consumer_task
    producer_thread.join(timeout=1.0)

    assert len(results) == 1
    assert results[0].content == final_msg.content

async def test_all_events_receives_status_change(streamer: AgentEventStream, real_notifier: AgentExternalEventNotifier, agent_id_fixture: str):
    """Tests that status change events are received by the unified stream."""
    async def produce_events():
        await asyncio.sleep(0.05)
        real_notifier.notify_status_updated(
            new_status=AgentStatus.IDLE,
            old_status=AgentStatus.BOOTSTRAPPING,
        )
        # DO NOT call streamer.close() from the producer thread.

    consumer_task = asyncio.create_task(_collect_stream_results(streamer.all_events()))
    
    producer_thread = run_producer_in_thread(produce_events())
    results = await consumer_task
    producer_thread.join(timeout=1.0)

    assert len(results) == 1
    event = results[0]
    assert isinstance(event, StreamEvent)
    assert event.agent_id == agent_id_fixture
    assert event.event_type == StreamEventType.AGENT_STATUS_UPDATED
    assert isinstance(event.data, AgentStatusUpdateData)
    assert event.data.new_status == AgentStatus.IDLE
    assert event.data.old_status == AgentStatus.BOOTSTRAPPING

async def test_all_events_receives_assistant_chunk(streamer: AgentEventStream, real_notifier: AgentExternalEventNotifier):
    """Tests that chunk events are received by the unified stream."""
    chunk = ChunkResponse(content="test chunk")
    
    async def produce_events():
        await asyncio.sleep(0.05)
        real_notifier.notify_agent_data_assistant_chunk(chunk)
        # DO NOT call streamer.close() from the producer thread.

    consumer_task = asyncio.create_task(_collect_stream_results(streamer.all_events()))
    
    producer_thread = run_producer_in_thread(produce_events())
    results = await consumer_task
    producer_thread.join(timeout=1.0)

    assert len(results) == 1
    event = results[0]
    assert event.event_type == StreamEventType.ASSISTANT_CHUNK
    assert isinstance(event.data, AssistantChunkData)
    assert event.data.content == "test chunk"

async def test_all_events_receives_complete_response(streamer: AgentEventStream, real_notifier: AgentExternalEventNotifier):
    """Tests that complete response events are received by the unified stream."""
    final_msg = CompleteResponse(content="Final response content.")
    
    async def produce_events():
        await asyncio.sleep(0.05)
        real_notifier.notify_agent_data_assistant_complete_response(final_msg)
        # DO NOT call streamer.close() from the producer thread.

    consumer_task = asyncio.create_task(_collect_stream_results(streamer.all_events()))
    
    producer_thread = run_producer_in_thread(produce_events())
    results = await consumer_task
    producer_thread.join(timeout=1.0)

    assert len(results) == 1
    event = results[0]
    assert event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE
    assert isinstance(event.data, AssistantCompleteResponseData)
    assert event.data.content == "Final response content."

async def test_all_events_receives_error(streamer: AgentEventStream, real_notifier: AgentExternalEventNotifier):
    """Tests that error events are received by the unified stream."""
    async def produce_events():
        await asyncio.sleep(0.05)
        real_notifier.notify_agent_error_output_generation(
            error_source="Test.Source",
            error_message="A test error occurred.",
            error_details="Detailed traceback."
        )
        # DO NOT call streamer.close() from the producer thread.

    consumer_task = asyncio.create_task(_collect_stream_results(streamer.all_events()))
    
    producer_thread = run_producer_in_thread(produce_events())
    results = await consumer_task
    producer_thread.join(timeout=1.0)

    assert len(results) == 1
    event = results[0]
    assert event.event_type == StreamEventType.ERROR_EVENT
    assert isinstance(event.data, ErrorEventData)
    assert event.data.source == "Test.Source"
    assert event.data.message == "A test error occurred."
    assert event.data.details == "Detailed traceback."

async def test_all_events_receives_multiple_mixed_events(streamer: AgentEventStream, real_notifier: AgentExternalEventNotifier):
    """Tests that a sequence of different events are all captured by the unified stream."""
    chunk1 = ChunkResponse(content="c1")
    final_msg = CompleteResponse(content="final")

    async def produce_events():
        await asyncio.sleep(0.02)
        real_notifier.notify_status_updated(
            new_status=AgentStatus.IDLE,
            old_status=AgentStatus.BOOTSTRAPPING,
        )
        await asyncio.sleep(0.02)
        real_notifier.notify_agent_data_assistant_chunk(chunk1)
        await asyncio.sleep(0.02)
        real_notifier.notify_agent_data_assistant_complete_response(final_msg)
        await asyncio.sleep(0.02)
        # DO NOT call streamer.close() from the producer thread.

    consumer_task = asyncio.create_task(_collect_stream_results(streamer.all_events()))
    
    producer_thread = run_producer_in_thread(produce_events())
    results = await consumer_task
    producer_thread.join(timeout=1.0)

    assert len(results) == 3
    assert results[0].event_type == StreamEventType.AGENT_STATUS_UPDATED
    assert results[1].event_type == StreamEventType.ASSISTANT_CHUNK
    assert results[2].event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE
