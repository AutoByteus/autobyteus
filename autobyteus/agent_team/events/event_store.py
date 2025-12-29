# file: autobyteus/autobyteus/agent_team/events/event_store.py
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    timestamp: float
    team_id: str
    event: BaseAgentTeamEvent
    correlation_id: Optional[str] = None
    caused_by_event_id: Optional[str] = None
    sequence: int = 0


class AgentTeamEventStore:
    """
    Simple in-memory event store for agent team events.
    """
    def __init__(self, team_id: str):
        self._team_id = team_id
        self._events: List[EventEnvelope] = []
        self._sequence: int = 0
        logger.debug(f"AgentTeamEventStore initialized for team_id '{team_id}'.")

    def append(self,
               event: BaseAgentTeamEvent,
               correlation_id: Optional[str] = None,
               caused_by_event_id: Optional[str] = None) -> EventEnvelope:
        envelope = EventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type=type(event).__name__,
            timestamp=time.time(),
            team_id=self._team_id,
            event=event,
            correlation_id=correlation_id,
            caused_by_event_id=caused_by_event_id,
            sequence=self._sequence,
        )
        self._sequence += 1
        self._events.append(envelope)
        logger.debug(f"Appended event '{envelope.event_type}' to store for team '{self._team_id}'.")
        return envelope

    def all_events(self) -> List[EventEnvelope]:
        return list(self._events)
