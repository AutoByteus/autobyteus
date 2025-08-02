# file: autobyteus/autobyteus/agent_team/streaming/agent_event_multiplexer.py
import asyncio
import logging
from typing import TYPE_CHECKING, Dict, Optional

from autobyteus.agent_team.streaming.agent_event_bridge import AgentEventBridge
from autobyteus.agent_team.streaming.team_event_bridge import TeamEventBridge

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent_team.agent_team import AgentTeam
    from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier
    from autobyteus.agent_team.runtime.agent_team_worker import AgentTeamWorker

logger = logging.getLogger(__name__)

class AgentEventMultiplexer:
    """
    Manages the lifecycle of event bridges for all nodes (agents and sub-teams).
    It creates, tracks, and shuts down the bridges that forward node events
    to the agent team's main event stream.
    """
    def __init__(self, team_id: str, notifier: 'AgentTeamExternalEventNotifier', worker_ref: 'AgentTeamWorker'):
        self._team_id = team_id
        self._notifier = notifier
        self._worker = worker_ref
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._agent_bridges: Dict[str, AgentEventBridge] = {}
        self._team_bridges: Dict[str, TeamEventBridge] = {}
        logger.info(f"AgentEventMultiplexer initialized for team '{self._team_id}'.")

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Retrieves the event loop from the worker on-demand."""
        if self._loop is None or self._loop.is_closed():
            self._loop = self._worker.get_worker_loop()
            if self._loop is None:
                raise RuntimeError(f"Agent team worker loop for team '{self._team_id}' is not available or not running.")
        return self._loop

    def start_bridging_agent_events(self, agent: 'Agent', agent_name: str):
        """Creates and starts an AgentEventBridge for a direct agent node."""
        if agent_name in self._agent_bridges:
            logger.warning(f"Event bridge for agent '{agent_name}' already exists. Skipping creation.")
            return

        bridge = AgentEventBridge(agent=agent, agent_name=agent_name, notifier=self._notifier, loop=self._get_loop())
        self._agent_bridges[agent_name] = bridge
        logger.info(f"AgentEventMultiplexer started agent event bridge for '{agent_name}'.")

    def start_bridging_team_events(self, sub_team: 'AgentTeam', node_name: str):
        """Creates and starts a TeamEventBridge for a sub-team node."""
        if node_name in self._team_bridges:
            logger.warning(f"Event bridge for sub-team '{node_name}' already exists. Skipping creation.")
            return
            
        bridge = TeamEventBridge(sub_team=sub_team, sub_team_node_name=node_name, parent_notifier=self._notifier, loop=self._get_loop())
        self._team_bridges[node_name] = bridge
        logger.info(f"AgentEventMultiplexer started team event bridge for '{node_name}'.")

    async def shutdown(self):
        """Gracefully shuts down all active event bridges."""
        logger.info(f"AgentEventMultiplexer for '{self._team_id}' shutting down all event bridges.")
        agent_bridge_tasks = [b.cancel() for b in self._agent_bridges.values()]
        team_bridge_tasks = [b.cancel() for b in self._team_bridges.values()]
        
        await asyncio.gather(*(agent_bridge_tasks + team_bridge_tasks), return_exceptions=True)
        
        self._agent_bridges.clear()
        self._team_bridges.clear()
        logger.info(f"All event bridges for team '{self._team_id}' have been shut down by multiplexer.")
