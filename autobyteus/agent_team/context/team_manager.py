# file: autobyteus/autobyteus/agent_team/context/team_manager.py
import asyncio
import logging
from typing import List, Dict, Optional, TYPE_CHECKING, Union

from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.utils.wait_for_idle import wait_for_agent_to_be_idle
from autobyteus.agent_team.utils.wait_for_idle import wait_for_team_to_be_idle
from autobyteus.agent_team.exceptions import TeamNodeNotFoundException

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent_team.agent_team import AgentTeam
    from autobyteus.agent_team.events.agent_team_events import InterAgentMessageRequestEvent, ProcessUserMessageEvent
    from autobyteus.agent_team.runtime.agent_team_runtime import AgentTeamRuntime
    from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer
    from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig

ManagedNode = Union['Agent', 'AgentTeam']

logger = logging.getLogger(__name__)

class TeamManager:
    """
    Manages all nodes (agents and sub-teams) within an agent team. It handles
    lazy creation, on-demand startup, and provides access to managed instances.
    It assumes all node names are unique within the team.
    """
    def __init__(self, team_id: str, runtime: 'AgentTeamRuntime', multiplexer: 'AgentEventMultiplexer'):
        self.team_id = team_id
        self._runtime = runtime
        self._multiplexer = multiplexer
        self._agent_factory = AgentFactory()
        self._nodes_cache: Dict[str, ManagedNode] = {}
        self._agent_id_to_name_map: Dict[str, str] = {}
        self._coordinator_agent: Optional['Agent'] = None
        logger.info(f"TeamManager created for team '{self.team_id}'.")

    async def dispatch_inter_agent_message_request(self, event: 'InterAgentMessageRequestEvent'):
        await self._runtime.submit_event(event)

    async def dispatch_user_message_to_agent(self, event: 'ProcessUserMessageEvent'):
        """Submits a user message event (potentially system-generated) to the team's runtime."""
        await self._runtime.submit_event(event)

    async def ensure_node_is_ready(self, name_or_agent_id: str) -> ManagedNode:
        """
        Retrieves a node by its unique name or ID. If not yet created, it
        instantiates and starts it on-demand.
        """
        unique_name: str
        if name_or_agent_id in self._agent_id_to_name_map:
            unique_name = self._agent_id_to_name_map[name_or_agent_id]
        else:
            unique_name = name_or_agent_id
            
        node_instance = self._nodes_cache.get(unique_name)
        
        was_created = False
        if not node_instance:
            logger.debug(f"Node '{unique_name}' not in cache for team '{self.team_id}'. Attempting lazy creation.")
            
            node_config_wrapper = self._runtime.context.get_node_config_by_name(unique_name)
            if not node_config_wrapper:
                raise TeamNodeNotFoundException(node_name=name_or_agent_id, team_id=self.team_id)

            if node_config_wrapper.is_sub_team:
                from autobyteus.agent_team.factory.agent_team_factory import AgentTeamFactory
                from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
                
                team_factory = AgentTeamFactory()
                node_definition = node_config_wrapper.node_definition
                if not isinstance(node_definition, AgentTeamConfig):
                     raise TypeError(f"Expected AgentTeamConfig for node '{unique_name}', but found {type(node_definition)}")
                logger.info(f"Lazily creating sub-team node '{unique_name}' in team '{self.team_id}'.")
                node_instance = team_factory.create_team(config=node_definition)
            else:
                # Agent creation is now simpler: just retrieve the pre-made config.
                final_config = self._runtime.context.state.final_agent_configs.get(unique_name)
                if not final_config:
                    raise RuntimeError(f"No pre-prepared agent configuration found for '{unique_name}'. "
                                     "Bootstrap step may have failed or skipped this agent.")
                
                logger.info(f"Lazily creating agent node '{unique_name}' using pre-prepared configuration.")
                node_instance = self._agent_factory.create_agent(config=final_config)
            
            self._nodes_cache[unique_name] = node_instance
            was_created = True

            from autobyteus.agent.agent import Agent
            if isinstance(node_instance, Agent):
                self._agent_id_to_name_map[node_instance.agent_id] = unique_name


        if was_created and node_instance:
            from autobyteus.agent_team.agent_team import AgentTeam
            from autobyteus.agent.agent import Agent
            if isinstance(node_instance, AgentTeam):
                self._multiplexer.start_bridging_team_events(node_instance, unique_name)
            elif isinstance(node_instance, Agent):
                self._multiplexer.start_bridging_agent_events(node_instance, unique_name)

        # On-Demand Startup Logic
        if not node_instance.is_running:
            from autobyteus.agent_team.agent_team import AgentTeam
            logger.info(f"Team '{self.team_id}': Node '{unique_name}' is not running. Starting on-demand.")
            await self._start_node(node_instance, unique_name)
        
        return node_instance

    async def _start_node(self, node: ManagedNode, name: str):
        """Starts a node and waits for it to be idle."""
        try:
            node.start()
            from autobyteus.agent_team.agent_team import AgentTeam
            if isinstance(node, AgentTeam):
                await wait_for_team_to_be_idle(node, timeout=120.0)
            else:
                await wait_for_agent_to_be_idle(node, timeout=60.0)
        except Exception as e:
            logger.error(f"Team '{self.team_id}': Failed to start node '{name}' on-demand: {e}", exc_info=True)
            raise RuntimeError(f"Failed to start node '{name}' on-demand.") from e

    def get_all_agents(self) -> List['Agent']:
        from autobyteus.agent.agent import Agent
        return [node for node in self._nodes_cache.values() if isinstance(node, Agent)]

    def get_all_sub_teams(self) -> List['AgentTeam']:
        from autobyteus.agent_team.agent_team import AgentTeam
        return [node for node in self._nodes_cache.values() if isinstance(node, AgentTeam)]

    @property
    def coordinator_agent(self) -> Optional['Agent']:
        return self._coordinator_agent

    async def ensure_coordinator_is_ready(self, coordinator_name: str) -> 'Agent':
        """
        Ensures the coordinator agent is created, started, and ready, then
        designates it as the coordinator.
        """
        from autobyteus.agent.agent import Agent
        node = await self.ensure_node_is_ready(name_or_agent_id=coordinator_name)
        if not isinstance(node, Agent):
            raise TypeError(f"Coordinator node '{coordinator_name}' resolved to a non-agent type: {type(node).__name__}")

        self._coordinator_agent = node
        return node
