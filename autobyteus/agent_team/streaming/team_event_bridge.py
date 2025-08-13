# file: autobyteus/autobyteus/agent_team/streaming/team_event_bridge.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.streaming.agent_team_event_stream import AgentTeamEventStream

if TYPE_CHECKING:
    from autobyteus.agent_team.agent_team import AgentTeam
    from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier

logger = logging.getLogger(__name__)

class TeamEventBridge:
    """
    A dedicated component that bridges events from a sub-team's event stream
    to the parent team's notifier.
    """
    def __init__(self, sub_team: 'AgentTeam', sub_team_node_name: str, parent_notifier: 'AgentTeamExternalEventNotifier', loop: asyncio.AbstractEventLoop):
        self._sub_team = sub_team
        self._sub_team_node_name = sub_team_node_name
        self._parent_notifier = parent_notifier
        self._stream = AgentTeamEventStream(sub_team)
        self._task: asyncio.Task = loop.create_task(self._run())
        logger.info(f"TeamEventBridge created and task started for sub-team '{sub_team_node_name}'.")

    async def _run(self):
        """The background task that consumes from the sub-team stream and re-publishes."""
        try:
            async for event in self._stream.all_events():
                # Re-broadcast the event to the parent, adding the sub-team context.
                self._parent_notifier.publish_sub_team_event(self._sub_team_node_name, event)
        except asyncio.CancelledError:
            logger.info(f"TeamEventBridge task for '{self._sub_team_node_name}' was cancelled.")
        except Exception as e:
            logger.error(f"Error in TeamEventBridge for '{self._sub_team_node_name}': {e}", exc_info=True)
        finally:
            logger.debug(f"TeamEventBridge task for '{self._sub_team_node_name}' is finishing.")

    async def cancel(self):
        """Gracefully stops the bridge."""
        logger.info(f"Cancelling TeamEventBridge for '{self._sub_team_node_name}'.")
        if not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass # Expected
        await self._stream.close()
        logger.info(f"TeamEventBridge for '{self._sub_team_node_name}' cancelled successfully.")
