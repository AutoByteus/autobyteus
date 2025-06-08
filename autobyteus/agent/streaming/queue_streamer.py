# file: autobyteus/autobyteus/agent/streaming/queue_streamer.py
import asyncio
import logging
from typing import TypeVar, AsyncIterator, Union, Any

# REMOVED: Import of END_OF_STREAM_SENTINEL as it's no longer globally defined
# from autobyteus.agent.events.agent_output_data_manager import END_OF_STREAM_SENTINEL

logger = logging.getLogger(__name__)

T = TypeVar('T')

async def stream_queue_items(
    queue: asyncio.Queue[Union[T, object]], 
    sentinel: object, 
    source_name: str = "unspecified_queue" 
) -> AsyncIterator[T]:
    """
    Asynchronously iterates over an asyncio.Queue, yielding items of type T
    until a specific sentinel object is encountered.

    Args:
        queue: The asyncio.Queue to stream items from.
        sentinel: The unique object used to signal the end of data in the queue.
        source_name: An optional identifier for the queue source, used in logging.

    Yields:
        Items of type T from the queue.

    Raises:
        TypeError: If queue is not an asyncio.Queue.
        ValueError: If sentinel is None.
        asyncio.CancelledError: If the generator is cancelled.
        Exception: Propagates exceptions encountered during queue.get().
    """
    if not isinstance(queue, asyncio.Queue):
        raise TypeError(f"queue must be an instance of asyncio.Queue for source '{source_name}'.")
    if sentinel is None: 
        raise ValueError(f"sentinel object cannot be None for source '{source_name}'.")

    logger.debug(f"Starting to stream items from queue '{source_name}'.")
    try:
        while True:
            item: Any = await queue.get() 
            if item is sentinel:
                logger.debug(f"Sentinel {sentinel!r} received from queue '{source_name}'. Ending stream.")
                queue.task_done() 
                break
            
            yield item # type: ignore 
            queue.task_done() 
    except asyncio.CancelledError:
        logger.info(f"Stream from queue '{source_name}' was cancelled.")
        raise 
    except Exception as e:
        logger.error(f"Error streaming from queue '{source_name}': {e}", exc_info=True)
        raise 
    finally:
        logger.debug(f"Exiting stream_queue_items for queue '{source_name}'.")

