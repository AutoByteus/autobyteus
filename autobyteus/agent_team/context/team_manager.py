# file: autobyteus/autobyteus/agent_team/context/team_manager.py
import asyncio
import logging
from typing import List, Dict, Optional, TYPE_CHECKING, Union

from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.utils.wait_for_idle import wait_for_agent_to_be_idle
from autobyteus.agent_team.utils.wait_for_idle import wait_for_team_to_be_idle
from autobyteus.agent_team.exceptions import TeamNodeNotFoundException
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.tools.registry import default_tool_registry

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent_team.agent_team import AgentTeam
    from autobyteus.agent_team.events.agent_team_events import InterAgentMessageRequestEvent
    from autobyteus.agent_team.runtime.agent_team_runtime import AgentTeamRuntime
    from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig

ManagedNode = Union['Agent', 'AgentTeam']

logger = logging.getLogger(__name__)

class TeamManager:
    """
    Manages all nodes (agents and sub-teams) within an agent team. It handles
    lazy creation, on-demand startup, and provides access to managed instances.
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

    async def ensure_node_is_ready(self, name: str) -> ManagedNode:
        """
        Retrieves a node (agent or sub-team) by its unique friendly name, alias,
        or full agent_id. If the node has not been created yet, it is instantiated.
        If it is not running, it is started and awaited until idle.
        Returns a fully ready node instance or raises an exception.
        """
        simple_name = name
        
        # 1. Resolve alias: Check if 'name' is a full agent_id we've already cached and translate to simple name.
        if simple_name in self._agent_id_to_name_map:
            simple_name = self._agent_id_to_name_map[simple_name]
        # 2. Resolve alias: If not, check if 'name' is a unique alias generated during bootstrap.
        elif self._runtime.context.state.node_alias_map and simple_name in self._runtime.context.state.node_alias_map:
            simple_name = self._runtime.context.state.node_alias_map[simple_name]

        # From here on, we use simple_name for cache and config lookups.
        node_instance = self._nodes_cache.get(simple_name)
        
        was_created = False
        if not node_instance:
            logger.debug(f"Node '{simple_name}' (resolved from '{name}') not in cache for team '{self.team_id}'. Attempting lazy creation.")
            
            node_config_wrapper = self._runtime.context.get_node_config_by_name(simple_name)
            if not node_config_wrapper:
                # The original name was not found in any map and does not match a config name.
                raise TeamNodeNotFoundException(node_name=name, team_id=self.team_id)

            node_definition = node_config_wrapper.node_definition

            if node_config_wrapper.is_sub_team:
                from autobyteus.agent_team.factory.agent_team_factory import AgentTeamFactory
                from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
                
                team_factory = AgentTeamFactory() # Get singleton instance
                if not isinstance(node_definition, AgentTeamConfig):
                     raise TypeError(f"Expected AgentTeamConfig for node '{simple_name}', but found {type(node_definition)}")
                logger.info(f"Lazily creating sub-team node '{simple_name}' in team '{self.team_id}'.")
                node_instance = team_factory.create_team(config=node_definition)
            else:
                from autobyteus.agent.context.agent_config import AgentConfig
                if not isinstance(node_definition, AgentConfig):
                     raise TypeError(f"Expected AgentConfig for node '{simple_name}', but found {type(node_definition)}")
                
                # --- Apply Deferred Logic from Bootstrap Step ---
                final_config = node_definition.copy()

                # 1. Inject SendMessageTo tool
                send_message_tool = default_tool_registry.create_tool(SendMessageTo.get_name())
                if isinstance(send_message_tool, SendMessageTo):
                    send_message_tool.set_team_manager(self)
                final_config.tools = [t for t in final_config.tools if not isinstance(t, SendMessageTo)]
                final_config.tools.append(send_message_tool)

                # 2. Apply coordinator prompt if this is the coordinator
                coordinator_node_name = self._runtime.context.config.coordinator_node.name
                if simple_name == coordinator_node_name:
                    coordinator_prompt = self._runtime.context.state.prepared_coordinator_prompt
                    if coordinator_prompt:
                        final_config.system_prompt = coordinator_prompt
                        logger.info(f"Applied dynamic prompt to coordinator '{simple_name}'.")
                
                logger.info(f"Lazily creating agent node '{simple_name}' in team '{self.team_id}'.")
                node_instance = self._agent_factory.create_agent(config=final_config)
            
            self._nodes_cache[simple_name] = node_instance
            was_created = True

            from autobyteus.agent.agent import Agent
            if isinstance(node_instance, Agent):
                self._agent_id_to_name_map[node_instance.agent_id] = simple_name


        if was_created and node_instance:
            from autobyteus.agent_team.agent_team import AgentTeam
            from autobyteus.agent.agent import Agent
            if isinstance(node_instance, AgentTeam):
                self._multiplexer.start_bridging_team_events(node_instance, simple_name)
            elif isinstance(node_instance, Agent):
                self._multiplexer.start_bridging_agent_events(node_instance, simple_name)

        # On-Demand Startup Logic
        if not node_instance.is_running:
            from autobyteus.agent_team.agent_team import AgentTeam
            logger.info(f"Team '{self.team_id}': Node '{simple_name}' is not running. Starting on-demand.")
            try:
                node_instance.start()
                if isinstance(node_instance, AgentTeam):
                    await wait_for_team_to_be_idle(node_instance, timeout=120.0)
                else:
                    await wait_for_agent_to_be_idle(node_instance, timeout=60.0)
            except Exception as e:
                logger.error(f"Team '{self.team_id}': Failed to start node '{simple_name}' on-demand: {e}", exc_info=True)
                raise RuntimeError(f"Failed to start node '{simple_name}' on-demand.") from e
        
        return node_instance

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
        node = await self.ensure_node_is_ready(coordinator_name)
        if not isinstance(node, Agent):
            raise TypeError(f"Coordinator node '{coordinator_name}' resolved to a non-agent type: {type(node).__name__}")

        self._coordinator_agent = node
        return node
