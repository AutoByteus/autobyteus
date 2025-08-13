# file: autobyteus/autobyteus/agent_team/streaming/agent_team_event_stream.py
import asyncio
import queue
from typing import AsyncIterator, TYPE_CHECKING

from autobyteus.events.event_types import EventType
from autobyteus.agent_team.streaming.agent_team_stream_events import AgentTeamStreamEvent
from autobyteus.agent.streaming.queue_streamer import stream_queue_items

if TYPE_CHECKING:
    from autobyteus.agent_team.agent_team import AgentTeam

_SENTINEL = object()

class AgentTeamEventStream:
    """Consumes events from an AgentTeamExternalEventNotifier for a specific team."""
    def __init__(self, team: 'AgentTeam'):
        self.team_id = team.team_id
        self._internal_q = queue.Queue()
        self._notifier = team._runtime.notifier
        self._notifier.subscribe(EventType.TEAM_STREAM_EVENT, self._handle_event)

    def _handle_event(self, payload: AgentTeamStreamEvent, **kwargs):
        if isinstance(payload, AgentTeamStreamEvent) and payload.team_id == self.team_id:
            self._internal_q.put(payload)

    async def close(self):
        self._notifier.unsubscribe(EventType.TEAM_STREAM_EVENT, self._handle_event)
        await asyncio.get_running_loop().run_in_executor(None, self._internal_q.put, _SENTINEL)

    def all_events(self) -> AsyncIterator[AgentTeamStreamEvent]:
        """The primary method to consume all structured events from the agent team."""
        return stream_queue_items(self._internal_q, _SENTINEL, f"team_{self.team_id}_stream")
