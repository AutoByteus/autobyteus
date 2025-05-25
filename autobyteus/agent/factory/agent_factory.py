# file: autobyteus/agent/factory/agent_factory.py
import logging
from typing import List, Union, Optional, Dict, cast, Type, TYPE_CHECKING, Any
from dataclasses import fields as dataclass_fields 

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.registry import ToolRegistry, default_tool_registry
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig 
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
from autobyteus.tools.base_tool import BaseTool 
# Import for the new System Prompt Processor system
from autobyteus.agent.system_prompt_processor import default_system_prompt_processor_registry, BaseSystemPromptProcessor


if TYPE_CHECKING:
    from autobyteus.agent.agent_runtime import AgentRuntime


logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory class for creating agents.
    This factory primarily creates AgentRuntime objects based on the 
    new architecture (AgentContext, AgentRuntime).
    It relies on ToolRegistry, LLMFactory, and SystemPromptProcessorRegistry.
    """
    # _TOOLS_PLACEHOLDER is no longer needed here, it's internal to ToolDescriptionInjectorProcessor

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
        self.system_prompt_processor_registry = default_system_prompt_processor_registry # Added registry
        logger.info("AgentFactory initialized with ToolRegistry, LLMFactory, and SystemPromptProcessorRegistry.")

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
                             llm_model_name: str, 
                             workspace: Optional[BaseAgentWorkspace] = None,
                             custom_llm_config: Optional[LLMConfig] = None,
                             custom_tool_config: Optional[Dict[str, ToolConfig]] = None,
                             auto_execute_tools_override: bool = True 
                             ) -> AgentContext: 
        logger.debug(f"Creating AgentContext for agent_id '{agent_id}' using definition '{definition.name}'. "
                     f"Workspace: {workspace is not None}. "
                     f"LLM Model Name: {llm_model_name if llm_model_name else 'None (Error if None)'}. "
                     f"Custom LLM Config provided: {custom_llm_config is not None}. "
                     f"Custom Tool Config Keys: {list(custom_tool_config.keys()) if custom_tool_config else 'None'}. "
                     f"Auto Execute Tools Override: {auto_execute_tools_override}.")

        if not isinstance(definition, AgentDefinition):
            raise TypeError(f"Expected AgentDefinition, got {type(definition).__name__}")
        if not llm_model_name or not isinstance(llm_model_name, str): 
            raise TypeError(f"An 'llm_model_name' (string) must be specified. Got {type(llm_model_name)}")
        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace):
             raise TypeError(f"Expected BaseAgentWorkspace or None for workspace, got {type(workspace).__name__}")
        if custom_llm_config is not None and not isinstance(custom_llm_config, LLMConfig): 
            raise TypeError(f"custom_llm_config must be an LLMConfig instance or None. Got {type(custom_llm_config)}")
        if custom_tool_config is not None and not (
            isinstance(custom_tool_config, dict) and
            all(isinstance(k, str) and isinstance(v, ToolConfig) for k, v in custom_tool_config.items())
        ):
            raise TypeError("custom_tool_config must be a Dict[str, ToolConfig] or None.")


        tool_instances_dict: Dict[str, BaseTool] = {} 
        try:
            for tool_name in definition.tool_names:
                tool_config_for_tool = custom_tool_config.get(tool_name) if custom_tool_config else None
                tool_instance = self.tool_registry.create_tool(tool_name, tool_config_for_tool)
                tool_instances_dict[tool_name] = tool_instance 
                
            logger.debug(f"Tools created for AgentContext '{agent_id}': {list(tool_instances_dict.keys())}")
        except Exception as e:
            logger.error(f"Error creating tools for AgentContext '{agent_id}': {e}")
            raise ValueError(f"Failed to create tools for AgentContext {agent_id} from definition '{definition.name}': {e}") from e

        # --- System Prompt Processing using new SystemPromptProcessor system ---
        current_system_prompt = definition.system_prompt # Start with the template from definition
        processor_names_to_apply = definition.system_prompt_processor_names
        
        if not processor_names_to_apply:
            logger.debug(f"Agent '{agent_id}': No system prompt processors configured in agent definition. Using system prompt as is.")
        else:
            logger.debug(f"Agent '{agent_id}': Applying system prompt processors: {processor_names_to_apply}")
            for processor_name in processor_names_to_apply:
                processor_instance = self.system_prompt_processor_registry.get_processor(processor_name)
                if processor_instance:
                    try:
                        logger.debug(f"Agent '{agent_id}': Applying system prompt processor '{processor_name}' (class: {processor_instance.__class__.__name__}).")
                        current_system_prompt = processor_instance.process(
                            system_prompt=current_system_prompt,
                            tool_instances=tool_instances_dict,
                            agent_id=agent_id
                        )
                        logger.info(f"Agent '{agent_id}': System prompt processor '{processor_name}' applied successfully.")
                    except Exception as e:
                        logger.error(f"Agent '{agent_id}': Error applying system prompt processor '{processor_name}': {e}. "
                                     f"Continuing with prompt from before this processor.", exc_info=True)
                        # current_system_prompt remains as it was before this failed processor
                else:
                    logger.warning(f"Agent '{agent_id}': System prompt processor name '{processor_name}' not found in registry. Skipping this processor.")
        
        processed_system_prompt = current_system_prompt # Final prompt after all processors
        # --- End System Prompt Processing ---

        try:
            try:
                llm_model_instance = LLMModel[llm_model_name]
            except KeyError:
                valid_model_names = [m.name for m in LLMModel] # Needs LLMFactory to be initialized
                logger.error(f"Invalid llm_model_name '{llm_model_name}' for retrieving default_config. Must be one of {valid_model_names}.")
                raise ValueError(f"Invalid llm_model_name '{llm_model_name}' for retrieving default_config. Valid names are: {valid_model_names}")
            
            config_source_log_parts = []

            if llm_model_instance.default_config:
                final_llm_config = LLMConfig.from_dict(llm_model_instance.default_config.to_dict())
                config_source_log_parts.append(f"base from model '{llm_model_name}'")
            else: 
                logger.warning(f"LLMModel '{llm_model_name}' does not have a default_config. Initializing LLMConfig with class defaults.")
                final_llm_config = LLMConfig()
                config_source_log_parts.append("LLMConfig class defaults")

            if custom_llm_config:
                logger.debug(f"Applying custom LLMConfig for agent '{agent_id}'. Custom temp: {custom_llm_config.temperature}")
                final_llm_config.merge_with(custom_llm_config)
                config_source_log_parts.append("merged with custom LLMConfig object")
            
            final_llm_config.system_message = processed_system_prompt 
            config_source_log_parts.append(f"system_prompt (processed, '{processed_system_prompt[:30]}...') applied")
            
            config_source_log = ", ".join(config_source_log_parts)

            llm_instance = self.llm_factory.create_llm(
                model_identifier=llm_model_name, 
                llm_config=final_llm_config
            )
            logger.debug(f"LLM instance created for AgentContext '{agent_id}'. "
                         f"Final LLM Config based on: {config_source_log}. Config details (sample): temp={final_llm_config.temperature}, sys_msg='{final_llm_config.system_message[:50]}...'")
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
                             llm_model_name: str, 
                             workspace: Optional[BaseAgentWorkspace] = None,
                             custom_llm_config: Optional[LLMConfig] = None, 
                             custom_tool_config: Optional[Dict[str, ToolConfig]] = None, 
                             auto_execute_tools_override: bool = True 
                             ) -> 'AgentRuntime': 
        from autobyteus.agent.agent_runtime import AgentRuntime 

        agent_context = self.create_agent_context(
            agent_id, 
            definition, 
            llm_model_name=llm_model_name, 
            workspace=workspace,
            custom_llm_config=custom_llm_config, 
            custom_tool_config=custom_tool_config, 
            auto_execute_tools_override=auto_execute_tools_override 
        )
        event_handler_registry = self._get_default_event_handler_registry()
        
        tool_exec_mode_log = "Automatic" if auto_execute_tools_override else "Requires Approval"
        logger.debug(f"Instantiating AgentRuntime for agent_id: '{agent_id}' with definition: '{definition.name}'. "
                     f"LLM Model Name: {llm_model_name}. Workspace provided: {workspace is not None}. Tool Execution Mode: {tool_exec_mode_log}")
        return AgentRuntime(context=agent_context, event_handler_registry=event_handler_registry)

