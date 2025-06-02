# file: autobyteus/autobyteus/agent/factory/agent_factory.py
import logging
from typing import List, Union, Optional, Dict, cast, Type, TYPE_CHECKING, Any

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.registry import ToolRegistry, default_tool_registry
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig

from autobyteus.agent.context.agent_config import AgentConfig 
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState 
from autobyteus.agent.context.agent_context import AgentContext 

from autobyteus.agent.events import AgentInputEventQueueManager 
from autobyteus.agent.events import AgentOutputDataManager      

from autobyteus.agent.events import ( 
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent, 
    PendingToolInvocationEvent, 
    ToolResultEvent,
    LLMCompleteResponseReceivedEvent, 
    GenericEvent, 
    AgentReadyEvent, # MODIFIED: Renamed from AgentStartedEvent
    AgentStoppedEvent,
    AgentErrorEvent,
    ToolExecutionApprovalEvent,
    LLMUserMessageReadyEvent, 
    ApprovedToolInvocationEvent,
    # Old preparation events - will not be registered by default
    # CreateToolInstancesEvent,
    # ProcessSystemPromptEvent,
    # FinalizeLLMConfigEvent,
    # CreateLLMInstanceEvent,
    BootstrapAgentEvent, 
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
    LLMUserMessageReadyEventHandler,
    # Old preparation handlers - will not be registered
    # CreateToolInstancesEventHandler,
    # ProcessSystemPromptEventHandler,
    # FinalizeLLMConfigEventHandler,
    # CreateLLMInstanceEventHandler,
    BootstrapAgentEventHandler, 
)
from autobyteus.agent.system_prompt_processor import default_system_prompt_processor_registry, SystemPromptProcessorRegistry


if TYPE_CHECKING:
    from autobyteus.agent.agent_runtime import AgentRuntime


logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory class for creating agents.
    This factory creates AgentConfig, AgentRuntimeState, the composite AgentContext, 
    and AgentRuntime objects.
    Tool and LLM instantiation is now orchestrated by BootstrapAgentEventHandler.
    It relies on ToolRegistry, LLMFactory, and SystemPromptProcessorRegistry.
    """

    def __init__(self,
                 tool_registry: ToolRegistry,
                 llm_factory: LLMFactory,
                 system_prompt_processor_registry: Optional[SystemPromptProcessorRegistry] = None): 
        if not isinstance(tool_registry, ToolRegistry): # pragma: no cover
            raise TypeError(f"AgentFactory 'tool_registry' must be an instance of ToolRegistry. Got {type(tool_registry)}")
        if not isinstance(llm_factory, LLMFactory): # pragma: no cover
            raise TypeError(f"AgentFactory 'llm_factory' must be an instance of LLMFactory. Got {type(llm_factory)}")
            
        self.tool_registry = tool_registry
        self.llm_factory = llm_factory
        self.system_prompt_processor_registry = system_prompt_processor_registry or default_system_prompt_processor_registry
        logger.info("AgentFactory initialized with ToolRegistry, LLMFactory, and SystemPromptProcessorRegistry.")

    def _get_default_event_handler_registry(self) -> EventHandlerRegistry:
        registry = EventHandlerRegistry()
        
        # Register the new BootstrapAgentEventHandler
        registry.register(
            BootstrapAgentEvent,
            BootstrapAgentEventHandler(
                tool_registry=self.tool_registry,
                system_prompt_processor_registry=self.system_prompt_processor_registry,
                llm_factory=self.llm_factory
            )
        )
        
        # REMOVED old individual initialization handlers
        # registry.register(
        #     CreateToolInstancesEvent,
        #     CreateToolInstancesEventHandler(tool_registry=self.tool_registry)
        # )
        # registry.register(
        #     ProcessSystemPromptEvent, 
        #     ProcessSystemPromptEventHandler(system_prompt_processor_registry=self.system_prompt_processor_registry)
        # )
        # registry.register(
        #     FinalizeLLMConfigEvent,
        #     FinalizeLLMConfigEventHandler() 
        # )
        # registry.register(
        #     CreateLLMInstanceEvent,
        #     CreateLLMInstanceEventHandler(llm_factory=self.llm_factory)
        # )
        
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
        registry.register(AgentReadyEvent, lifecycle_logger_instance) # MODIFIED: AgentReadyEvent
        registry.register(AgentStoppedEvent, lifecycle_logger_instance)
        registry.register(AgentErrorEvent, lifecycle_logger_instance)
        
        logger.debug(f"Default EventHandlerRegistry created with handlers for: {[cls.__name__ for cls in registry.get_all_registered_event_types()]}")
        return registry

    def _create_agent_config_and_state(self,
                                agent_id: str,
                                definition: AgentDefinition,
                                llm_model_name: str,
                                workspace: Optional[BaseAgentWorkspace] = None,
                                custom_llm_config: Optional[LLMConfig] = None,
                                custom_tool_config: Optional[Dict[str, ToolConfig]] = None,
                                auto_execute_tools: bool = True 
                                ) -> tuple[AgentConfig, AgentRuntimeState]:
        logger.debug(f"Creating AgentConfig for agent_id '{agent_id}' using definition '{definition.name}'. "
                     f"LLM Model Name: {llm_model_name}. Auto Execute: {auto_execute_tools}.")

        if not isinstance(definition, AgentDefinition): # pragma: no cover
            raise TypeError(f"Expected AgentDefinition, got {type(definition).__name__}")
        if not llm_model_name or not isinstance(llm_model_name, str):  # pragma: no cover
            raise TypeError(f"An 'llm_model_name' (string) must be specified. Got {type(llm_model_name)}")
        if custom_llm_config is not None and not isinstance(custom_llm_config, LLMConfig):  # pragma: no cover
            raise TypeError(f"custom_llm_config must be an LLMConfig instance or None. Got {type(custom_llm_config)}")
        if custom_tool_config is not None and not ( # pragma: no cover
            isinstance(custom_tool_config, dict) and
            all(isinstance(k, str) and isinstance(v, ToolConfig) for k, v in custom_tool_config.items())
        ): 
            raise TypeError("custom_tool_config must be a Dict[str, ToolConfig] or None.")
        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace): # pragma: no cover
             raise TypeError(f"Expected BaseAgentWorkspace or None for workspace, got {type(workspace).__name__}")

        agent_config = AgentConfig(
            agent_id=agent_id,
            definition=definition,
            auto_execute_tools=auto_execute_tools, 
            llm_model_name=llm_model_name,
            custom_llm_config=custom_llm_config,
            custom_tool_config=custom_tool_config
        )
        logger.info(f"AgentConfig created for agent_id '{agent_id}'.")

        input_event_queues = AgentInputEventQueueManager() 
        output_data_queues = AgentOutputDataManager()

        agent_runtime_state = AgentRuntimeState(
            agent_id=agent_id, 
            input_event_queues=input_event_queues,   
            output_data_queues=output_data_queues,   
            workspace=workspace,
        )
        logger.info(f"AgentRuntimeState created for agent_id '{agent_id}'.")
        
        return agent_config, agent_runtime_state


    def create_agent_context(self, 
                             agent_id: str, 
                             definition: AgentDefinition, 
                             llm_model_name: str, 
                             workspace: Optional[BaseAgentWorkspace] = None,
                             custom_llm_config: Optional[LLMConfig] = None,
                             custom_tool_config: Optional[Dict[str, ToolConfig]] = None,
                             auto_execute_tools: bool = True 
                             ) -> AgentContext: 
        agent_config, agent_runtime_state = self._create_agent_config_and_state(
            agent_id=agent_id,
            definition=definition,
            llm_model_name=llm_model_name,
            workspace=workspace,
            custom_llm_config=custom_llm_config,
            custom_tool_config=custom_tool_config,
            auto_execute_tools=auto_execute_tools 
        )
        
        composite_context = AgentContext(config=agent_config, state=agent_runtime_state)
        logger.info(f"Composite AgentContext created for agent_id '{agent_id}'.")
        return composite_context

    def create_agent_runtime(self, 
                             agent_id: str, 
                             definition: AgentDefinition,
                             llm_model_name: str, 
                             workspace: Optional[BaseAgentWorkspace] = None,
                             custom_llm_config: Optional[LLMConfig] = None, 
                             custom_tool_config: Optional[Dict[str, ToolConfig]] = None, 
                             auto_execute_tools: bool = True 
                             ) -> 'AgentRuntime': 
        from autobyteus.agent.agent_runtime import AgentRuntime 

        composite_agent_context = self.create_agent_context(
            agent_id=agent_id, 
            definition=definition, 
            llm_model_name=llm_model_name, 
            workspace=workspace,
            custom_llm_config=custom_llm_config, 
            custom_tool_config=custom_tool_config,
            auto_execute_tools=auto_execute_tools 
        )
        
        event_handler_registry = self._get_default_event_handler_registry()
        
        tool_exec_mode_log = "Automatic" if auto_execute_tools else "Requires Approval" 
        logger.info(f"Instantiating AgentRuntime for agent_id: '{agent_id}' with definition: '{definition.name}'. "
                     f"LLM Model Name (for init): {llm_model_name}. Workspace: {workspace is not None}. Tool Exec Mode: {tool_exec_mode_log}")
        
        return AgentRuntime(context=composite_agent_context, event_handler_registry=event_handler_registry)
