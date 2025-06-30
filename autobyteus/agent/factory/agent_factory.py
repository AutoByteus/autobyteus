# file: autobyteus/autobyteus/agent/factory/agent_factory.py
import logging
import random
from typing import Optional, TYPE_CHECKING, Dict, List

# LLMFactory is no longer needed here.
from autobyteus.agent.agent import Agent
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState 
from autobyteus.agent.context.agent_context import AgentContext 
from autobyteus.agent.events import *
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace 
from autobyteus.agent.handlers import *
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.runtime.agent_runtime import AgentRuntime

logger = logging.getLogger(__name__)

class AgentFactory(metaclass=SingletonMeta):
    """
    A singleton factory class for creating and managing agent instances.
    This is the primary entry point for creating new agents.
    This factory is now decoupled from LLMFactory.
    """

    def __init__(self):
        self._active_agents: Dict[str, Agent] = {}
        logger.info("AgentFactory (Singleton) initialized.")

    def _get_default_event_handler_registry(self) -> EventHandlerRegistry:
        registry = EventHandlerRegistry()
        registry.register(UserMessageReceivedEvent, UserInputMessageEventHandler())
        registry.register(InterAgentMessageReceivedEvent, InterAgentMessageReceivedEventHandler())
        registry.register(LLMCompleteResponseReceivedEvent, LLMCompleteResponseReceivedEventHandler())
        registry.register(PendingToolInvocationEvent, ToolInvocationRequestEventHandler())
        registry.register(ToolResultEvent, ToolResultEventHandler())
        registry.register(GenericEvent, GenericEventHandler())
        registry.register(ToolExecutionApprovalEvent, ToolExecutionApprovalEventHandler())
        registry.register(LLMUserMessageReadyEvent, LLMUserMessageReadyEventHandler())
        registry.register(ApprovedToolInvocationEvent, ApprovedToolInvocationEventHandler())
        lifecycle_logger_instance = LifecycleEventLogger()
        registry.register(AgentReadyEvent, lifecycle_logger_instance)
        registry.register(AgentStoppedEvent, lifecycle_logger_instance)
        registry.register(AgentErrorEvent, lifecycle_logger_instance)
        return registry

    def _prepare_tool_instances(self, agent_id: str, config: AgentConfig) -> Dict[str, BaseTool]:
        """
        Prepares the tool instance dictionary from the provided list of tool instances.
        """
        tool_instances_dict: Dict[str, BaseTool] = {}
        if not config.tools:
            logger.info(f"Agent '{agent_id}': No tools provided in config.")
            return tool_instances_dict

        for tool_instance in config.tools:
            if not isinstance(tool_instance, BaseTool):
                 # This should ideally be caught by AgentConfig's type hints, but serves as a runtime safeguard.
                raise TypeError(f"Invalid item in tool list for agent '{agent_id}': {type(tool_instance)}. Expected an instance of BaseTool.")
            
            instance_name = tool_instance.get_name()
            if instance_name in tool_instances_dict:
                logger.warning(f"Agent '{agent_id}': Duplicate tool name '{instance_name}' encountered. The last one will be used.")
            
            tool_instances_dict[instance_name] = tool_instance
        
        return tool_instances_dict

    def _create_runtime(self, 
                        agent_id: str, 
                        config: AgentConfig
                        ) -> 'AgentRuntime': 
        from autobyteus.agent.runtime.agent_runtime import AgentRuntime 

        # The workspace and initial custom data are now passed directly from the config to the state.
        runtime_state = AgentRuntimeState(
            agent_id=agent_id,
            workspace=config.workspace,
            custom_data=config.initial_custom_data
        )
        
        # --- Set pre-initialized instances on the state ---
        runtime_state.llm_instance = config.llm_instance
        runtime_state.tool_instances = self._prepare_tool_instances(agent_id, config)
        
        logger.info(f"Agent '{agent_id}': LLM instance '{config.llm_instance.__class__.__name__}' and {len(runtime_state.tool_instances)} tools prepared and stored in state.")

        context = AgentContext(agent_id=agent_id, config=config, state=runtime_state)
        event_handler_registry = self._get_default_event_handler_registry()
        
        logger.info(f"Instantiating AgentRuntime for agent_id: '{agent_id}' with config: '{config.name}'.")
        
        return AgentRuntime(
            context=context, 
            event_handler_registry=event_handler_registry
        )

    def create_agent(
        self,
        config: AgentConfig
    ) -> Agent:
        """
        Creates a new agent based on the provided AgentConfig, stores it,
        and returns its facade (Agent class). The agent_id is automatically generated.
        """
        if not isinstance(config, AgentConfig):
            raise TypeError(f"Expected AgentConfig instance, got {type(config).__name__}.")

        random_part = random.randint(1000, 9999)
        agent_id = f"{config.name}_{config.role}_{random_part}"
        while agent_id in self._active_agents:
            agent_id = f"{config.name}_{config.role}_{random.randint(1000, 9999)}"

        runtime = self._create_runtime(
            agent_id=agent_id,
            config=config,
        )

        agent = Agent(runtime=runtime)
        self._active_agents[agent_id] = agent
        logger.info(f"Agent '{agent_id}' created and stored successfully.")
        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Retrieves an active agent instance by its ID."""
        return self._active_agents.get(agent_id)

    async def remove_agent(self, agent_id: str, shutdown_timeout: float = 10.0) -> bool:
        """
        Removes an agent from the factory's management and gracefully stops it.
        """
        agent = self._active_agents.pop(agent_id, None)
        if agent:
            logger.info(f"Removing agent '{agent_id}'. Attempting graceful shutdown.")
            await agent.stop(timeout=shutdown_timeout)
            return True
        logger.warning(f"Agent with ID '{agent_id}' not found for removal.")
        return False

    def list_active_agent_ids(self) -> List[str]:
        """Returns a list of IDs of all active agents managed by this factory."""
        return list(self._active_agents.keys())
