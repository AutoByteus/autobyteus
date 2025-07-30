# file: autobyteus/autobyteus/workflow/context/team_manager.py
import asyncio
import logging
from typing import List, Dict, Optional, TYPE_CHECKING

from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.utils.wait_for_idle import wait_for_agent_to_be_idle

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent
    from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
    from autobyteus.workflow.streaming.agent_event_multiplexer import AgentEventMultiplexer

logger = logging.getLogger(__name__)

class TeamManager:
    """
    Manages agents within a workflow, handling lazy creation, on-demand startup,
    and event stream multiplexing.
    """
    def __init__(self, workflow_id: str, runtime: 'WorkflowRuntime', multiplexer: 'AgentEventMultiplexer'):
        self.workflow_id = workflow_id
        self._runtime = runtime
        self._multiplexer = multiplexer
        self._agent_factory = AgentFactory()
        self._agents_cache: Dict[str, 'Agent'] = {}
        self._coordinator_agent: Optional['Agent'] = None
        self._final_agent_configs: Dict[str, AgentConfig] = {}
        logger.info(f"TeamManager created for workflow '{self.workflow_id}'.")

    def set_agent_configs(self, configs: Dict[str, AgentConfig]):
        self._final_agent_configs = configs
        logger.info(f"TeamManager for workflow '{self.workflow_id}' populated with {len(configs)} final agent configs.")

    async def dispatch_inter_agent_message_request(self, event: 'InterAgentMessageRequestEvent'):
        await self._runtime.submit_event(event)

    async def ensure_agent_is_ready(self, name: str) -> Optional['Agent']:
        """
        Retrieves an agent by its unique friendly name. If the agent has not
        been created yet, it is instantiated. If it is not running, it is
        started and awaited until idle. Returns a fully ready agent or None on failure.
        """
        agent = self._agents_cache.get(name)
        was_created = False
        if not agent:
            agent_config = self._final_agent_configs.get(name)
            if not agent_config:
                logger.error(f"No prepared config for agent '{name}' in workflow '{self.workflow_id}'.")
                return None

            logger.info(f"Lazily creating agent '{name}' in workflow '{self.workflow_id}'.")
            agent = self._agent_factory.create_agent(config=agent_config)
            self._agents_cache[name] = agent
            was_created = True
        
        if was_created:
            # Trigger the multiplexer to start bridging events for the new agent.
            self._multiplexer.start_bridging_agent_events(agent, name)
        
        # --- On-Demand Startup Logic ---
        if not agent.is_running:
            logger.info(f"Workflow '{self.workflow_id}': Agent '{name}' is not running. Starting on-demand.")
            try:
                agent.start()
                await wait_for_agent_to_be_idle(agent, timeout=60.0)
            except Exception as e:
                logger.error(f"Workflow '{self.workflow_id}': Failed to start agent '{name}' on-demand: {e}", exc_info=True)
                # Return None to signal failure to the caller
                return None
        
        return agent

    def get_all_agents(self) -> List['Agent']:
        return list(self._agents_cache.values())

    @property
    def coordinator_agent(self) -> Optional['Agent']:
        return self._coordinator_agent

    async def ensure_coordinator_is_ready(self, coordinator_name: str) -> 'Agent':
        """
        Ensures the coordinator agent is created, started, and ready, then
        designates it as the coordinator.
        """
        agent = await self.ensure_agent_is_ready(coordinator_name)
        if not agent:
            raise ValueError(f"Could not create and ready coordinator agent for name '{coordinator_name}'.")

        self._coordinator_agent = agent
        return agent
