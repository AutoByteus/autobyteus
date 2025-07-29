# file: autobyteus/autobyteus/workflow/context/team_manager.py
import logging
from typing import List, Dict, Optional, TYPE_CHECKING

from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.context.agent_config import AgentConfig

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent
    from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime

logger = logging.getLogger(__name__)

class TeamManager:
    """
    Manages the agents within a workflow, supporting on-demand (lazy) creation.
    It is the single source of truth for the agent team and uses pre-prepared
    agent configurations provided during the workflow's bootstrap phase.
    """
    def __init__(self, workflow_id: str, runtime: 'WorkflowRuntime'):
        self.workflow_id = workflow_id
        self._runtime = runtime
        self._agent_factory = AgentFactory()
        self._agents_cache: Dict[str, 'Agent'] = {}
        self._coordinator_agent: Optional['Agent'] = None
        self._final_agent_configs: Dict[str, AgentConfig] = {}
        logger.info(f"TeamManager created for workflow '{self.workflow_id}'. Awaiting agent configs.")

    def set_agent_configs(self, configs: Dict[str, AgentConfig]):
        """
        Populates the manager with the final, prepared agent configurations.
        This is called by a bootstrap step.
        """
        self._final_agent_configs = configs
        logger.info(f"TeamManager for workflow '{self.workflow_id}' populated with {len(configs)} final agent configs.")

    async def dispatch_inter_agent_message_request(self, event: 'InterAgentMessageRequestEvent'):
        """Forwards an event from a tool to the main workflow runtime."""
        logger.debug(f"TeamManager for workflow '{self.workflow_id}' dispatching event {type(event).__name__} to runtime.")
        await self._runtime.submit_event(event)

    def get_agent_by_friendly_name(self, name: str) -> Optional['Agent']:
        """
        Retrieves an agent by its unique friendly name. If the agent has not
        been created yet, it is instantiated, configured, and cached using
        its pre-prepared configuration.
        """
        if name in self._agents_cache:
            return self._agents_cache[name]

        agent_config = self._final_agent_configs.get(name)
        if not agent_config:
            logger.error(f"No prepared agent configuration found for friendly name '{name}' in workflow '{self.workflow_id}'.")
            return None

        logger.info(f"Lazily creating agent for node '{name}' in workflow '{self.workflow_id}'.")
        
        # Create the agent instance using the pre-prepared config
        agent = self._agent_factory.create_agent(config=agent_config)
        
        # Inject self for further agent discovery (e.g., finding team members by role)
        agent.context.custom_data['team_manager'] = self

        logger.info(f"Agent '{agent.agent_id}' (friendly name: {name}) created and configured.")
        self._agents_cache[name] = agent
        return agent

    def get_all_agents(self) -> List['Agent']:
        """Returns all agents that have been instantiated so far."""
        return list(self._agents_cache.values())

    @property
    def coordinator_agent(self) -> Optional['Agent']:
        """Returns the coordinator agent instance, if it has been created."""
        return self._coordinator_agent

    def get_and_configure_coordinator(self, coordinator_name: str) -> 'Agent':
        """
        Eagerly creates the coordinator agent by its friendly name and
        sets it as the coordinator.
        """
        logger.info(f"Eagerly creating coordinator agent '{coordinator_name}' in workflow '{self.workflow_id}'.")
        agent = self.get_agent_by_friendly_name(coordinator_name)
        if not agent:
            raise ValueError(f"Could not create coordinator agent for name '{coordinator_name}'.")

        self._coordinator_agent = agent
        return agent
