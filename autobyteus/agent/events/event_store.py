# file: autobyteus/autobyteus/agent/events/event_store.py
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

from autobyteus.agent.events.agent_events import BaseEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    timestamp: float
    agent_id: str
    event: BaseEvent
    correlation_id: Optional[str] = None
    caused_by_event_id: Optional[str] = None
    sequence: int = 0


class AgentEventStore:
    """
    Simple in-memory event store for agent events.
    """
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._events: List[EventEnvelope] = []
        self._sequence: int = 0
        logger.debug(f"AgentEventStore initialized for agent_id '{agent_id}'.")

    def append(self,
               event: BaseEvent,
               correlation_id: Optional[str] = None,
               caused_by_event_id: Optional[str] = None) -> EventEnvelope:
        envelope = EventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type=type(event).__name__,
            timestamp=time.time(),
            agent_id=self._agent_id,
            event=event,
            correlation_id=correlation_id,
            caused_by_event_id=caused_by_event_id,
            sequence=self._sequence,
        )
        self._sequence += 1
        self._events.append(envelope)
        logger.debug(f"Appended event '{envelope.event_type}' to store for agent '{self._agent_id}'.")
        return envelope

    def all_events(self) -> List[EventEnvelope]:
        return list(self._events)
