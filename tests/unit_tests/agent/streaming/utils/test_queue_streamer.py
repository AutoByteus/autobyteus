# file: autobyteus/tests/unit_tests/agent/streaming/test_queue_streamer.py
import asyncio
import pytest
import queue as standard_queue
from typing import List, Any, AsyncIterator

from autobyteus.agent.streaming.utils.queue_streamer import stream_queue_items

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def sentinel() -> object:
    """Fixture for a unique sentinel object."""
    return object()

@pytest.fixture
def queue() -> standard_queue.Queue:
    """Fixture for an empty standard_queue.Queue."""
    return standard_queue.Queue()

async def _collect_stream_results(stream: AsyncIterator[Any]) -> List[Any]:
    """Helper function to collect all items from an async iterator into a list."""
    results = []
    async for item in stream:
        results.append(item)
    return results

async def test_normal_operation(queue: standard_queue.Queue, sentinel: object):
    """Test streaming items until sentinel is encountered."""
    items_to_add = [1, "two", {"three": 3}, [4, 4.0]]
    for item in items_to_add:
        queue.put(item)
    queue.put(sentinel)

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == items_to_add
    assert queue.empty()

async def test_empty_queue_then_sentinel(queue: standard_queue.Queue, sentinel: object):
    """Test streaming when queue is initially empty, then sentinel is added."""
    
    async def add_sentinel_later():
        await asyncio.sleep(0.01)
        queue.put(sentinel)

    asyncio.create_task(add_sentinel_later())
    
    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == []
    assert queue.empty()

async def test_sentinel_first(queue: standard_queue.Queue, sentinel: object):
    """Test streaming when sentinel is the first item."""
    queue.put(sentinel)
    queue.put(1)

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == []
    assert not queue.empty()
    assert queue.get() == 1

async def test_multiple_items_before_sentinel(queue: standard_queue.Queue, sentinel: object):
    """Test with multiple items ensuring all are yielded in order."""
    items_to_add = list(range(10))
    for item in items_to_add:
        queue.put(item)
    queue.put(sentinel)

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == items_to_add

@pytest.mark.parametrize("data_item", [
    100, "hello world", {"key": "value", "nested": [1, 2]}, [True, False, None], 42.75
])
async def test_various_data_types(queue: standard_queue.Queue, sentinel: object, data_item: Any):
    """Test streaming with different data types."""
    queue.put(data_item)
    queue.put(sentinel)

    results = await _collect_stream_results(stream_queue_items(queue, sentinel))
    assert results == [data_item]

async def test_invalid_queue_type(sentinel: object):
    """Test TypeError when a non-Queue object is passed."""
    with pytest.raises(TypeError, match="queue must be an instance of queue.Queue"):
        async for _ in stream_queue_items(list(), sentinel): # type: ignore
            pass

async def test_none_sentinel_value(queue: standard_queue.Queue):
    """Test ValueError when sentinel is None."""
    with pytest.raises(ValueError, match="sentinel object cannot be None"):
        async for _ in stream_queue_items(queue, None):
            pass

async def test_cancellation_during_streaming(queue: standard_queue.Queue, sentinel: object):
    """Test behavior when the stream_queue_items generator is cancelled."""
    queue.put(1)
    queue.put(2)
    # Sentinel not added yet

    stream_gen = stream_queue_items(queue, sentinel)
    
    task = asyncio.create_task(_collect_stream_results(stream_gen))
    await asyncio.sleep(0.01)
    
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # Unblock any pending executor call waiting on queue.get.
    queue.put(sentinel)
    await asyncio.sleep(0.01)

async def test_stream_with_source_name(queue: standard_queue.Queue, sentinel: object, caplog):
    """Test that source_name is used in logging."""
    import logging
    caplog.set_level(logging.DEBUG)

    custom_source_name = "my_custom_test_queue"
    queue.put("data")
    queue.put(sentinel)

    await _collect_stream_results(stream_queue_items(queue, sentinel, source_name=custom_source_name))
    
    log_messages = [record.message for record in caplog.records]
    assert f"Starting to stream items from queue '{custom_source_name}'." in log_messages
    assert f"Sentinel {sentinel!r} received from queue '{custom_source_name}'. Ending stream." in log_messages
    assert f"Exiting stream_queue_items for queue '{custom_source_name}'." in log_messages
