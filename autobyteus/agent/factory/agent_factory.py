# file: autobyteus/agent/factory/agent_factory.py
import logging
from typing import List, Union, Optional, Dict, cast, Type, TYPE_CHECKING, Any

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.registry import ToolRegistry, default_tool_registry
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.llm.models import LLMModel, LLMConfig
from autobyteus.agent.context import AgentContext 
from autobyteus.agent.events import AgentEventQueues 
from autobyteus.agent.events import ( 
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent, 
    PendingToolInvocationEvent, 
    ToolResultEvent,
    LLMCompleteResponseReceivedEvent, 
    GenericEvent, 
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    ToolExecutionApprovalEvent,
    LLMPromptReadyEvent,
    ApprovedToolInvocationEvent, 
)
from autobyteus.agent.registry.agent_definition import AgentDefinition 
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace 
from autobyteus.agent.handlers import ( 
    UserInputMessageEventHandler,
    InterAgentMessageReceivedEventHandler, 
    ToolInvocationRequestEventHandler,
    ToolResultEventHandler,
    LLMCompleteResponseReceivedEventHandler, 
    GenericEventHandler, 
    EventHandlerRegistry,
    LifecycleEventLogger, 
    ToolExecutionApprovalEventHandler,
    ApprovedToolInvocationEventHandler, 
)
from autobyteus.agent.handlers.llm_prompt_ready_event_handler import LLMPromptReadyEventHandler


if TYPE_CHECKING:
    from autobyteus.agent.agent_runtime import AgentRuntime


logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory class for creating agents.
    This factory primarily creates AgentRuntime objects based on the 
    new architecture (AgentContext, AgentRuntime).
    It relies on ToolRegistry and LLMFactory for creating tools and LLM instances.
    """
    def __init__(self,
                 tool_registry: ToolRegistry,
                 llm_factory: LLMFactory): 
        """
        Initializes the AgentFactory.

        Args:
            tool_registry: An instance of ToolRegistry.
            llm_factory: An instance of LLMFactory.
        """
        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError(f"AgentFactory 'tool_registry' must be an instance of ToolRegistry. Got {type(tool_registry)}")
        if not isinstance(llm_factory, LLMFactory):
            raise TypeError(f"AgentFactory 'llm_factory' must be an instance of LLMFactory. Got {type(llm_factory)}")
            
        self.tool_registry = tool_registry
        self.llm_factory = llm_factory
        logger.info("AgentFactory initialized with ToolRegistry and LLMFactory.")

    def _get_default_event_handler_registry(self) -> EventHandlerRegistry:
        registry = EventHandlerRegistry()
        
        registry.register(UserMessageReceivedEvent, UserInputMessageEventHandler())
        registry.register(InterAgentMessageReceivedEvent, InterAgentMessageReceivedEventHandler()) 
        registry.register(LLMCompleteResponseReceivedEvent, LLMCompleteResponseReceivedEventHandler())
        registry.register(PendingToolInvocationEvent, ToolInvocationRequestEventHandler()) 
        registry.register(ToolResultEvent, ToolResultEventHandler())
        registry.register(GenericEvent, GenericEventHandler())
        registry.register(ToolExecutionApprovalEvent, ToolExecutionApprovalEventHandler())
        registry.register(LLMPromptReadyEvent, LLMPromptReadyEventHandler())
        registry.register(ApprovedToolInvocationEvent, ApprovedToolInvocationEventHandler()) 
        
        lifecycle_logger_instance = LifecycleEventLogger() 
        registry.register(AgentStartedEvent, lifecycle_logger_instance)
        registry.register(AgentStoppedEvent, lifecycle_logger_instance)
        registry.register(AgentErrorEvent, lifecycle_logger_instance)
        
        logger.debug(f"Default EventHandlerRegistry created with handlers for: {[cls.__name__ for cls in registry.get_all_registered_event_types()]}")
        return registry

    def create_agent_context(self, 
                             agent_id: str, 
                             definition: AgentDefinition, 
                             llm_model: LLMModel,
                             workspace: Optional[BaseAgentWorkspace] = None,
                             llm_config_override: Optional[Dict[str, Any]] = None,
                             tool_config_override: Optional[Dict[str, ToolConfig]] = None,
                             auto_execute_tools_override: bool = True 
                             ) -> AgentContext: 
        logger.debug(f"Creating AgentContext for agent_id '{agent_id}' using definition '{definition.name}'. "
                     f"Workspace: {workspace is not None}. "
                     f"LLM Model: {llm_model.value if llm_model else 'None (Error if None)'}. "
                     f"LLM Config Override Keys: {list(llm_config_override.keys()) if llm_config_override else 'None'}. "
                     f"Tool Config Override Keys: {list(tool_config_override.keys()) if tool_config_override else 'None'}. "
                     f"Auto Execute Tools Override: {auto_execute_tools_override}.")

        if not isinstance(definition, AgentDefinition):
            raise TypeError(f"Expected AgentDefinition, got {type(definition).__name__}")
        if not isinstance(llm_model, LLMModel):
            raise TypeError(f"An 'llm_model' of type LLMModel must be specified. Got {type(llm_model)}")
        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace):
             raise TypeError(f"Expected BaseAgentWorkspace or None for workspace, got {type(workspace).__name__}")

        try:
            tool_instances_dict = {}
            for tool_name in definition.tool_names:
                # Get tool-specific config if provided
                tool_config = tool_config_override.get(tool_name) if tool_config_override else None
                tool_instance = self.tool_registry.create_tool(tool_name, tool_config)
                tool_instances_dict[tool_name] = tool_instance
                
            logger.debug(f"Tools created for AgentContext '{agent_id}': {list(tool_instances_dict.keys())}")
        except Exception as e:
            logger.error(f"Error creating tools for AgentContext '{agent_id}': {e}")
            raise ValueError(f"Failed to create tools for AgentContext {agent_id} from definition '{definition.name}': {e}") from e

        try:
            final_llm_model: LLMModel = llm_model 
            model_source = "direct parameter"
            
            logger.info(f"LLM model for agent '{agent_id}': '{final_llm_model.value}' (Source: {model_source})")

            base_config_params = {}
            if hasattr(final_llm_model, 'default_config') and final_llm_model.default_config is not None:
                 if isinstance(final_llm_model.default_config, LLMConfig):
                    base_config_params = final_llm_model.default_config.to_dict()
                 elif isinstance(final_llm_model.default_config, dict): 
                    base_config_params = final_llm_model.default_config.copy()
                 else:
                    logger.warning(f"Model '{final_llm_model.value}' has an unexpected default_config type: {type(final_llm_model.default_config)}. Initializing with empty config.")
            
            merged_config_data = base_config_params
            config_source_log = f"base from model '{final_llm_model.value}'"
            
            if llm_config_override: 
                merged_config_data.update(llm_config_override)
                config_source_log += ", updated by explicit overrides"

            merged_config_data['system_message'] = definition.system_prompt
            config_source_log += ", system_prompt from AgentDefinition applied"
            
            final_llm_config = LLMConfig(**merged_config_data)
            
            llm_instance = self.llm_factory.create_llm(
                model_identifier=final_llm_model.name, 
                custom_config=final_llm_config
            )
            logger.debug(f"LLM instance created for AgentContext '{agent_id}'. "
                         f"Final LLM Config based on: {config_source_log}. Config details: {final_llm_config.to_dict()}")
        except Exception as e:
            logger.error(f"Error creating LLM for AgentContext '{agent_id}': {e}", exc_info=True)
            raise ValueError(f"Failed to create LLM for AgentContext {agent_id}: {e}") from e

        queues = AgentEventQueues() 

        agent_context = AgentContext(
            agent_id=agent_id,
            definition=definition, 
            queues=queues,
            llm_instance=llm_instance,
            tool_instances=tool_instances_dict,
            workspace=workspace,
            auto_execute_tools=auto_execute_tools_override 
        )
        return agent_context

    def create_agent_runtime(self, 
                             agent_id: str, 
                             definition: AgentDefinition,
                             llm_model: LLMModel,
                             workspace: Optional[BaseAgentWorkspace] = None,
                             llm_config_override: Optional[Dict[str, Any]] = None,
                             tool_config_override: Optional[Dict[str, ToolConfig]] = None,
                             auto_execute_tools_override: bool = True 
                             ) -> 'AgentRuntime': 
        from autobyteus.agent.agent_runtime import AgentRuntime 

        agent_context = self.create_agent_context(
            agent_id, 
            definition, 
            llm_model=llm_model,
            workspace=workspace,
            llm_config_override=llm_config_override,
            tool_config_override=tool_config_override,
            auto_execute_tools_override=auto_execute_tools_override 
        )
        event_handler_registry = self._get_default_event_handler_registry()
        
        tool_exec_mode_log = "Automatic" if auto_execute_tools_override else "Requires Approval"
        logger.debug(f"Instantiating AgentRuntime for agent_id: '{agent_id}' with definition: '{definition.name}'. "
                     f"LLM Model: {llm_model.value}. Workspace provided: {workspace is not None}. Tool Execution Mode: {tool_exec_mode_log}")
        return AgentRuntime(context=agent_context, event_handler_registry=event_handler_registry)
