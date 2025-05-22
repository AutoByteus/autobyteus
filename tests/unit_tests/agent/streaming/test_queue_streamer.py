# file: autobyteus/tests/unit_tests/agent/streaming/test_queue_streamer.py
import asyncio
import pytest
from typing import List, Any, AsyncIterator

from autobyteus.agent.streaming.queue_streamer import stream_queue_items

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def sentinel() -> object:
    """Fixture for a unique sentinel object."""
    return object()

@pytest.fixture
def queue() -> asyncio.Queue:
    """Fixture for an empty asyncio.Queue."""
    return asyncio.Queue()

async def _collect_stream_results(stream: AsyncIterator[Any]) -> List[Any]:
    """Helper function to collect all items from an async iterator into a list."""
    results = []
    async for item in stream:
        results.append(item)
    return results

async def test_normal_operation(queue: asyncio.Queue, sentinel: object):
    """Test streaming items until sentinel is encountered."""
    items_to_add = [1, "two", {"three": 3}, [4, 4.0]]
    for item in items_to_add:
        await queue.put(item)
    await queue.put(sentinel)

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == items_to_add
    assert queue.empty() # Sentinel should be consumed, and task_done called for all

async def test_empty_queue_then_sentinel(queue: asyncio.Queue, sentinel: object):
    """Test streaming when queue is initially empty, then sentinel is added."""
    
    async def add_sentinel_later():
        await asyncio.sleep(0.01) # Ensure stream_queue_items starts waiting
        await queue.put(sentinel)

    asyncio.create_task(add_sentinel_later())
    
    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == []
    assert queue.empty()

async def test_sentinel_first(queue: asyncio.Queue, sentinel: object):
    """Test streaming when sentinel is the first item."""
    await queue.put(sentinel)
    await queue.put(1) # This item should not be yielded

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == []
    # Queue may not be empty if item after sentinel was added, but stream_queue_items should have exited.
    # The function's responsibility is to stop at sentinel.
    # `queue.get()` for the sentinel and `task_done()` has been called.
    # The remaining '1' will still be in the queue.
    assert not queue.empty()
    assert await queue.get() == 1


async def test_multiple_items_before_sentinel(queue: asyncio.Queue, sentinel: object):
    """Test with multiple items ensuring all are yielded in order."""
    items_to_add = list(range(10))
    for item in items_to_add:
        await queue.put(item)
    await queue.put(sentinel)

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == items_to_add

@pytest.mark.parametrize("data_item", [
    100, "hello world", {"key": "value", "nested": [1, 2]}, [True, False, None], 42.75
])
async def test_various_data_types(queue: asyncio.Queue, sentinel: object, data_item: Any):
    """Test streaming with different data types."""
    await queue.put(data_item)
    await queue.put(sentinel)

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == [data_item]

async def test_invalid_queue_type(sentinel: object):
    """Test TypeError when a non-Queue object is passed."""
    with pytest.raises(TypeError, match="queue must be an instance of asyncio.Queue"):
        async for _ in stream_queue_items(list(), sentinel): # type: ignore
            pass # Should not reach here

async def test_none_sentinel_value(queue: asyncio.Queue):
    """Test ValueError when sentinel is None."""
    with pytest.raises(ValueError, match="sentinel object cannot be None"):
        async for _ in stream_queue_items(queue, None):
            pass # Should not reach here

async def test_cancellation_during_streaming(queue: asyncio.Queue, sentinel: object):
    """Test behavior when the stream_queue_items generator is cancelled."""
    await queue.put(1)
    await queue.put(2)
    # Sentinel not added yet, so stream would block on queue.get()

    stream_gen = stream_queue_items(queue, sentinel)
    
    task = asyncio.create_task(_collect_stream_results(stream_gen))

    # Let the task run a bit to consume initial items
    await asyncio.sleep(0.01) 
    
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    
    # The primary assertion is that `asyncio.CancelledError` is raised and propagated.
    # State of the queue and consumed items before cancellation can be complex to assert
    # reliably due to timing of cancellation, so we focus on error propagation.

async def test_stream_with_source_name(queue: asyncio.Queue, sentinel: object, caplog):
    """Test that source_name is used in logging."""
    import logging # Import locally if only used here, or at top if widely used
    caplog.set_level(logging.DEBUG)

    custom_source_name = "my_custom_test_queue"
    await queue.put("data")
    await queue.put(sentinel)

    await _collect_stream_results(stream_queue_items(queue, sentinel, source_name=custom_source_name))
    
    log_messages = [record.message for record in caplog.records]
    assert f"Starting to stream items from queue '{custom_source_name}'." in log_messages
    assert f"Sentinel {sentinel!r} received from queue '{custom_source_name}'. Ending stream." in log_messages
    assert f"Exiting stream_queue_items for queue '{custom_source_name}'." in log_messages


async def test_task_done_called_for_each_item(queue: asyncio.Queue, sentinel: object):
    """Test that queue.task_done() is called for each yielded item and the sentinel."""
    items_to_add = [1, 2, 3]
    for item in items_to_add:
        await queue.put(item)
    await queue.put(sentinel)

    stream_task = asyncio.create_task(
        _collect_stream_results(stream_queue_items(queue, sentinel))
    )

    results = await stream_task
    assert results == items_to_add
    
    try:
        await asyncio.wait_for(queue.join(), timeout=0.1)
    except asyncio.TimeoutError:
        pytest.fail("queue.join() timed out, implies task_done() was not called for all items.")
    
    assert queue.empty()

