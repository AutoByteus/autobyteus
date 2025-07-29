# file: autobyteus/autobyteus/agent/workflow/events/workflow_input_event_queue_manager.py
import asyncio
import logging
from typing import Any

from .workflow_events import ProcessRequestEvent

logger = logging.getLogger(__name__)

class WorkflowInputEventQueueManager:
    """Manages asyncio.Queue instances for events consumed by the WorkflowWorker."""
    def __init__(self, queue_size: int = 0):
        self.process_request_queue: asyncio.Queue[ProcessRequestEvent] = asyncio.Queue(maxsize=queue_size)
        self.internal_system_event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_size)
        logger.info("WorkflowInputEventQueueManager initialized.")

    async def enqueue_process_request(self, event: ProcessRequestEvent):
        await self.process_request_queue.put(event)

    async def enqueue_internal_system_event(self, event: Any):
        await self.internal_system_event_queue.put(event)
