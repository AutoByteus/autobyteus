# file: autobyteus/autobyteus/agent_team/streaming/agent_event_bridge.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.streaming.agent_event_stream import AgentEventStream

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier

logger = logging.getLogger(__name__)

class AgentEventBridge:
    """
    A dedicated component that bridges events from a single agent's event stream
    to the main team notifier. This is the core of the multiplexing pattern.
    """
    def __init__(self, agent: 'Agent', agent_name: str, notifier: 'AgentTeamExternalEventNotifier', loop: asyncio.AbstractEventLoop):
        self._agent_name = agent_name
        self._notifier = notifier
        self._stream = AgentEventStream(agent)
        self._task: asyncio.Task = loop.create_task(self._run())
        logger.info(f"AgentEventBridge created and task started for agent '{agent_name}'.")

    async def _run(self):
        """The background task that consumes from the stream and publishes to the notifier."""
        try:
            async for event in self._stream.all_events():
                self._notifier.publish_agent_event(self._agent_name, event)
        except asyncio.CancelledError:
            logger.info(f"AgentEventBridge task for '{self._agent_name}' was cancelled.")
        except Exception as e:
            logger.error(f"Error in AgentEventBridge for '{self._agent_name}': {e}", exc_info=True)
        finally:
            logger.debug(f"AgentEventBridge task for '{self._agent_name}' is finishing.")

    async def cancel(self):
        """Gracefully stops the bridge."""
        logger.info(f"Cancelling AgentEventBridge for '{self._agent_name}'.")
        if not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass # Expected
        await self._stream.close()
        logger.info(f"AgentEventBridge for '{self._agent_name}' cancelled successfully.")
