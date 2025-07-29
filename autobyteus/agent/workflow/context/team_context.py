# file: autobyteus/autobyteus/agent/workflow/context/team_context.py
import logging
import copy
from typing import List, Dict, Optional, TYPE_CHECKING, Callable, Awaitable

from ....agent.factory import AgentFactory
from ....agent.message.send_message_to import SendMessageTo
from ..comm.workflow_communicator import WorkflowCommunicator
from ....agent.context.agent_config import AgentConfig

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from .workflow_node_config import WorkflowNodeConfig
    from ..events.workflow_events import BaseWorkflowEvent

logger = logging.getLogger(__name__)

class TeamContext:
    """
    Manages the agents within a workflow, supporting on-demand (lazy) creation.
    It holds the logic for instantiating member agents and performing dependency
    injection for workflow-aware components, like the SendMessageTo tool.
    """
    def __init__(self,
                 workflow_id: str,
                 node_configs_by_friendly_name: Dict[str, 'WorkflowNodeConfig'],
                 submit_event_callback: Callable[['BaseWorkflowEvent'], Awaitable[None]]):
        self.workflow_id = workflow_id
        self._node_configs = node_configs_by_friendly_name
        self._agent_factory = AgentFactory()
        self._agents_cache: Dict[str, 'Agent'] = {}
        self._communicator = WorkflowCommunicator(submit_event_callback=submit_event_callback)
        logger.info(f"TeamContext created for workflow '{workflow_id}' with {len(self._node_configs)} lazy-loaded agents.")

    def _prepare_config(self, agent_config: AgentConfig) -> AgentConfig:
        """
        Ensures the agent's config has necessary workflow-related components,
        like the SendMessageTo tool. This returns a new, modified AgentConfig.
        """
        new_config = copy.deepcopy(agent_config)
        
        has_send_message_tool = any(isinstance(tool, SendMessageTo) for tool in new_config.tools)
        
        if not has_send_message_tool:
            new_config.tools.append(SendMessageTo())
            logger.debug(f"Added SendMessageTo tool to config for agent '{new_config.name}'.")

        return new_config

    def _configure_agent_runtime(self, agent: 'Agent'):
        """Injects runtime dependencies into a newly created agent."""
        # Inject the communicator for upward communication to the workflow
        agent.context.state.workflow_communicator = self._communicator
        
        # Inject self for team-related lookups (e.g., finding peers)
        agent.context.custom_data['team_context'] = self
        logger.debug(f"Injected workflow communicator and team context into runtime for agent '{agent.agent_id}'.")

    def get_agent_by_friendly_name(self, name: str) -> Optional['Agent']:
        """
        Retrieves an agent by its unique friendly name. If the agent has not
        been created yet, it is instantiated, configured, and cached.
        """
        if name in self._agents_cache:
            return self._agents_cache[name]

        node_config = self._node_configs.get(name)
        if not node_config:
            logger.error(f"No node configuration found for friendly name '{name}' in workflow '{self.workflow_id}'.")
            return None

        logger.info(f"Lazily creating agent for node '{name}' in workflow '{self.workflow_id}'.")
        
        # Get the original config and create a new one with dependencies injected
        prepared_config = self._prepare_config(node_config.effective_config)

        # Create the agent instance using the modified config
        agent = self._agent_factory.create_agent(config=prepared_config)
        
        # Inject runtime dependencies
        self._configure_agent_runtime(agent)

        logger.info(f"Agent '{agent.agent_id}' (friendly name: {name}) created and configured.")
        self._agents_cache[name] = agent
        return agent

    def get_all_agents(self) -> List['Agent']:
        """Returns all agents that have been instantiated so far."""
        return list(self._agents_cache.values())

    @property
    def communicator(self) -> 'WorkflowCommunicator':
        return self._communicator

    def get_and_configure_coordinator(self, coordinator_config: AgentConfig) -> 'Agent':
        """
        Eagerly creates the coordinator agent, injects its dependencies, and
        caches it.
        """
        logger.info(f"Eagerly creating coordinator agent '{coordinator_config.name}' in workflow '{self.workflow_id}'.")
        
        prepared_config = self._prepare_config(coordinator_config)
        agent = self._agent_factory.create_agent(config=prepared_config)
        
        # Inject runtime dependencies
        self._configure_agent_runtime(agent)
        
        # Cache the coordinator using its own name as the key
        self._agents_cache[agent.context.config.name] = agent
        return agent
