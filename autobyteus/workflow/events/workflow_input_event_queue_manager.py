# file: autobyteus/autobyteus/workflow/events/workflow_input_event_queue_manager.py
import asyncio
import logging
from typing import Any

from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent

logger = logging.getLogger(__name__)

class WorkflowInputEventQueueManager:
    """Manages asyncio.Queue instances for events consumed by the WorkflowWorker."""
    def __init__(self, queue_size: int = 0):
        self.user_message_queue: asyncio.Queue[ProcessUserMessageEvent] = asyncio.Queue(maxsize=queue_size)
        self.internal_system_event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_size)
        logger.info("WorkflowInputEventQueueManager initialized.")

    async def enqueue_user_message(self, event: ProcessUserMessageEvent):
        await self.user_message_queue.put(event)

    async def enqueue_internal_system_event(self, event: Any):
        await self.internal_system_event_queue.put(event)
