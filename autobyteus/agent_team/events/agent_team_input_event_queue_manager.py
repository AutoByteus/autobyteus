# file: autobyteus/autobyteus/agent_team/events/agent_team_input_event_queue_manager.py
import asyncio
import logging
from typing import Any

from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent

logger = logging.getLogger(__name__)

class AgentTeamInputEventQueueManager:
    """Manages asyncio.Queue instances for events consumed by the AgentTeamWorker."""
    def __init__(self, queue_size: int = 0):
        self.user_message_queue: asyncio.Queue[ProcessUserMessageEvent] = asyncio.Queue(maxsize=queue_size)
        self.internal_system_event_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_size)
        logger.info("AgentTeamInputEventQueueManager initialized.")

    async def enqueue_user_message(self, event: ProcessUserMessageEvent):
        await self.user_message_queue.put(event)

    async def enqueue_internal_system_event(self, event: Any):
        await self.internal_system_event_queue.put(event)
