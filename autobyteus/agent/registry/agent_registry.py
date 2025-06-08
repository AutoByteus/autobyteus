import asyncio
import logging
import uuid 
import random
from typing import Dict, List, Optional, cast, Any 

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.agent import Agent 
from autobyteus.agent.runtime.agent_runtime import AgentRuntime
from autobyteus.agent.registry.agent_definition import AgentDefinition 
from autobyteus.agent.registry.agent_definition_registry import AgentDefinitionRegistry
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace 

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.registry import ToolRegistry, default_tool_registry
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.llm.models import LLMModel 
from autobyteus.llm.utils.llm_config import LLMConfig

logger = logging.getLogger(__name__)

class AgentRegistry(metaclass=SingletonMeta):
    """
    A singleton registry that creates, stores, and retrieves active agent instances
    (represented by Agent).
    """

    def __init__(self, agent_factory: AgentFactory, definition_registry: AgentDefinitionRegistry):
        """
        Initializes the AgentRegistry.
        Args:
            agent_factory: The AgentFactory instance used to create agent runtimes.
            definition_registry: An instance of AgentDefinitionRegistry.
        """
        self.agent_factory = agent_factory
        self.definition_registry = definition_registry 
        self._active_agents: Dict[str, Agent] = {} 
        logger.info("AgentRegistry initialized. Ready to create and manage Agent instances.")

    def create_agent(self, 
                     definition: AgentDefinition,
                     llm_model_name: str, 
                     workspace: Optional[BaseAgentWorkspace] = None,
                     custom_llm_config: Optional[LLMConfig] = None,
                     custom_tool_config: Optional[Dict[str, ToolConfig]] = None, 
                     auto_execute_tools: bool = True # NO CHANGE TO NAME, this is fine
                     ) -> Agent: 
        """
        Creates a new agent based on the provided AgentDefinition, stores it,
        and returns its facade (Agent class). The agent_id is automatically generated
        using the agent's name, role, and a random number.
        The `llm_model_name` (string) must be provided.
        Allows overriding LLM config (as LLMConfig object), tool configs, 
        and tool execution mode at instantiation.
        """
        if definition is None:
            msg = "AgentDefinition cannot be None."
            logger.error(f"Cannot create agent: {msg}")
            raise ValueError(msg)
        
        if not isinstance(definition, AgentDefinition):
            msg = f"Expected AgentDefinition instance, got {type(definition).__name__}."
            logger.error(f"Cannot create agent: {msg}")
            raise TypeError(msg)
        
        if not llm_model_name or not isinstance(llm_model_name, str): 
            msg = f"An 'llm_model_name' (string) must be specified. Got {type(llm_model_name)}."
            logger.error(f"Cannot create agent: {msg}")
            raise TypeError(msg)

        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace):
            raise TypeError(f"Expected BaseAgentWorkspace or None for workspace, got {type(workspace).__name__}")
        
        # Validate new custom_llm_config type
        if custom_llm_config is not None and not isinstance(custom_llm_config, LLMConfig):
            raise TypeError(f"custom_llm_config must be an LLMConfig instance or None. Got {type(custom_llm_config)}")
        
        if custom_tool_config is not None and not (
            isinstance(custom_tool_config, dict) and 
            all(isinstance(k, str) and isinstance(v, ToolConfig) for k, v in custom_tool_config.items())
        ):
            raise TypeError("custom_tool_config must be a Dict[str, ToolConfig] or None.")


        # Generate agent_id using name, role, and random number
        random_number = random.randint(1000, 9999)
        final_agent_id = f"{definition.name}_{definition.role}_{random_number}"
        
        # Handle collisions by generating new random numbers
        while final_agent_id in self._active_agents:
            logger.warning(f"Generated agent_id {final_agent_id} collided, regenerating with new random number.")
            random_number = random.randint(1000, 9999)
            final_agent_id = f"{definition.name}_{definition.role}_{random_number}"
        
        logger.info(f"Generated agent_id '{final_agent_id}' for definition '{definition.name}' with role '{definition.role}'")

        tool_exec_mode_log = "Automatic" if auto_execute_tools else "Requires Approval" # UPDATED LOGGING
        logger.info(f"Attempting to create agent runtime for definition_name '{definition.name}' "
                    f"with agent_id '{final_agent_id}'. "
                    f"Workspace provided: {workspace is not None}. "
                    f"LLM Model Name: {llm_model_name}. " 
                    f"Custom LLM Config provided: {custom_llm_config is not None}. "
                    f"Custom Tool Config Keys: {list(custom_tool_config.keys()) if custom_tool_config else 'None'}. "
                    f"Tool Execution Mode: {tool_exec_mode_log}.")
        
        runtime_instance: AgentRuntime = self.agent_factory.create_agent_runtime(
            agent_id=final_agent_id, 
            definition=definition,
            llm_model_name=llm_model_name, 
            workspace=workspace,
            custom_llm_config=custom_llm_config, 
            custom_tool_config=custom_tool_config,          
            auto_execute_tools=auto_execute_tools
        )
        
        agent_instance = Agent(runtime=runtime_instance) 
        
        self._active_agents[final_agent_id] = agent_instance 
        logger.info(f"Agent for agent_id '{final_agent_id}' (from definition '{definition.name}') " 
                    f"created and stored successfully. Workspace ID (if any): '{workspace.workspace_id if workspace else 'N/A'}'")

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

default_definition_registry = AgentDefinitionRegistry()

default_agent_factory = AgentFactory(
    tool_registry=default_tool_registry, 
    llm_factory=LLMFactory()
)

default_agent_registry = AgentRegistry(
    agent_factory=default_agent_factory,
    definition_registry=default_definition_registry
)
