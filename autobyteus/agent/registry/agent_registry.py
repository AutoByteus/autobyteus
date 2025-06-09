# file: autobyteus/autobyteus/agent/registry/agent_registry.py
import asyncio
import logging
import random
from typing import Dict, List, Optional, Any

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.agent import Agent
from autobyteus.agent.runtime.agent_runtime import AgentRuntime
from autobyteus.agent.registry.agent_specification import AgentSpecification
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.llm.utils.llm_config import LLMConfig

logger = logging.getLogger(__name__)

class AgentRegistry(metaclass=SingletonMeta):
    """
    A singleton registry that creates, stores, and retrieves active agent instances
    (represented by Agent). It uses an AgentFactory to construct the agent's runtime components.
    """

    def __init__(self, agent_factory: AgentFactory):
        """
        Initializes the AgentRegistry.
        Args:
            agent_factory: The AgentFactory instance used to create agent runtimes.
        """
        self.agent_factory = agent_factory
        self._active_agents: Dict[str, Agent] = {}
        logger.info("AgentRegistry initialized. Ready to create and manage Agent instances.")

    def create_agent(
        self,
        specification: AgentSpecification,
        llm_model_name: str,
        workspace: Optional[BaseAgentWorkspace] = None,
        custom_llm_config: Optional[LLMConfig] = None,
        custom_tool_config: Optional[Dict[str, ToolConfig]] = None,
        auto_execute_tools: bool = True
    ) -> Agent:
        """
        Creates a new agent based on the provided AgentSpecification, stores it,
        and returns its facade (Agent class). The agent_id is automatically generated.
        """
        if not isinstance(specification, AgentSpecification):
            raise TypeError(f"Expected AgentSpecification instance, got {type(specification).__name__}.")

        random_number = random.randint(1000, 9999)
        final_agent_id = f"{specification.name}_{specification.role}_{random_number}"

        while final_agent_id in self._active_agents:
            logger.warning(f"Generated agent_id {final_agent_id} collided, regenerating.")
            random_number = random.randint(1000, 9999)
            final_agent_id = f"{specification.name}_{specification.role}_{random_number}"

        runtime_instance: AgentRuntime = self.agent_factory.create_agent_runtime(
            agent_id=final_agent_id,
            specification=specification,
            llm_model_name=llm_model_name,
            workspace=workspace,
            custom_llm_config=custom_llm_config,
            custom_tool_config=custom_tool_config,
            auto_execute_tools=auto_execute_tools
        )

        agent_instance = Agent(runtime=runtime_instance)
        self._active_agents[final_agent_id] = agent_instance
        logger.info(f"Agent for agent_id '{final_agent_id}' (from spec '{specification.name}') created and stored successfully.")
        return agent_instance

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        agent_instance = self._active_agents.get(agent_id)
        if agent_instance is None:
            logger.debug(f"Agent with ID '{agent_id}' not found in registry.")
        return agent_instance

    async def remove_agent(self, agent_id: str, shutdown_timeout: float = 10.0) -> bool:
        agent_instance = self._active_agents.pop(agent_id, None)
        if agent_instance:
            logger.info(f"Removing Agent for ID '{agent_id}'. Attempting graceful shutdown.")
            try:
                await agent_instance.stop(timeout=shutdown_timeout)
                logger.info(f"Agent '{agent_id}' stopped successfully during removal.")
            except Exception as e:
                logger.error(f"Error stopping agent '{agent_id}' during removal: {e}", exc_info=True)
            return True
        else:
            logger.warning(f"Agent with ID '{agent_id}' not found for removal.")
            return False

    def list_active_agent_ids(self) -> List[str]:
        return list(self._active_agents.keys())

# Create default instances for the library to use
default_agent_factory = AgentFactory(
    tool_registry=default_tool_registry,
    llm_factory=LLMFactory()
)

default_agent_registry = AgentRegistry(
    agent_factory=default_agent_factory
)
