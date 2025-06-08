# file: autobyteus/autobyteus/agent/streaming/queue_streamer.py
import asyncio
import logging
from typing import TypeVar, AsyncIterator, Union, Any
import queue as standard_queue

logger = logging.getLogger(__name__)

T = TypeVar('T')

async def stream_queue_items(
    queue: standard_queue.Queue[Union[T, object]], 
    sentinel: object, 
    source_name: str = "unspecified_queue" 
) -> AsyncIterator[T]:
    """
    Asynchronously iterates over a standard `queue.Queue`, yielding items of type T
    until a specific sentinel object is encountered. This is designed to be used
    from an async context to consume from a queue populated by a synchronous/threaded context.

    Args:
        queue: The standard `queue.Queue` to stream items from.
        sentinel: The unique object used to signal the end of data in the queue.
        source_name: An optional identifier for the queue source, used in logging.

    Yields:
        Items of type T from the queue.

    Raises:
        TypeError: If queue is not a `queue.Queue`.
        ValueError: If sentinel is None.
        asyncio.CancelledError: If the generator is cancelled.
        Exception: Propagates exceptions encountered during queue.get().
    """
    if not isinstance(queue, standard_queue.Queue):
        raise TypeError(f"queue must be an instance of queue.Queue for source '{source_name}'.")
    if sentinel is None: 
        raise ValueError(f"sentinel object cannot be None for source '{source_name}'.")

    logger.debug(f"Starting to stream items from queue '{source_name}'.")
    loop = asyncio.get_running_loop()
    try:
        while True:
            # Use run_in_executor to wait for the blocking get() call without blocking the event loop.
            item: Any = await loop.run_in_executor(None, queue.get) 
            if item is sentinel:
                logger.debug(f"Sentinel {sentinel!r} received from queue '{source_name}'. Ending stream.")
                break
            
            yield item # type: ignore 
    except asyncio.CancelledError:
        logger.info(f"Stream from queue '{source_name}' was cancelled.")
        raise 
    except Exception as e:
        logger.error(f"Error streaming from queue '{source_name}': {e}", exc_info=True)
        raise 
    finally:
        logger.debug(f"Exiting stream_queue_items for queue '{source_name}'.")
