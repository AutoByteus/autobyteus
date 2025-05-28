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
    LLMUserMessageReadyEvent, 
    ApprovedToolInvocationEvent,
    CreateToolInstancesEvent,
    ProcessSystemPromptEvent,
    FinalizeLLMConfigEvent,
    CreateLLMInstanceEvent,
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
    CreateToolInstancesEventHandler,
    ProcessSystemPromptEventHandler,
    FinalizeLLMConfigEventHandler,
    CreateLLMInstanceEventHandler,
)
# BaseTool no longer needed for direct instantiation here
from autobyteus.agent.system_prompt_processor import default_system_prompt_processor_registry, SystemPromptProcessorRegistry


if TYPE_CHECKING:
    from autobyteus.agent.agent_runtime import AgentRuntime


logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory class for creating agents.
    This factory creates AgentConfig, AgentRuntimeState, the composite AgentContext, 
    and AgentRuntime objects.
    Tool and LLM instantiation is deferred to a chain of event handlers after agent startup.
    It relies on ToolRegistry, LLMFactory, and SystemPromptProcessorRegistry.
    """

    def __init__(self,
                 tool_registry: ToolRegistry,
                 llm_factory: LLMFactory,
                 system_prompt_processor_registry: Optional[SystemPromptProcessorRegistry] = None): 
        if not isinstance(tool_registry, ToolRegistry):
            raise TypeError(f"AgentFactory 'tool_registry' must be an instance of ToolRegistry. Got {type(tool_registry)}")
        if not isinstance(llm_factory, LLMFactory):
            raise TypeError(f"AgentFactory 'llm_factory' must be an instance of LLMFactory. Got {type(llm_factory)}")
            
        self.tool_registry = tool_registry
        self.llm_factory = llm_factory
        self.system_prompt_processor_registry = system_prompt_processor_registry or default_system_prompt_processor_registry
        logger.info("AgentFactory initialized with ToolRegistry, LLMFactory, and SystemPromptProcessorRegistry.")

    def _get_default_event_handler_registry(self) -> EventHandlerRegistry:
        registry = EventHandlerRegistry()
        
        # Initialization Sequence Handlers
        registry.register(
            CreateToolInstancesEvent,
            CreateToolInstancesEventHandler(tool_registry=self.tool_registry)
        )
        registry.register(
            ProcessSystemPromptEvent, 
            ProcessSystemPromptEventHandler(system_prompt_processor_registry=self.system_prompt_processor_registry)
        )
        registry.register(
            FinalizeLLMConfigEvent,
            FinalizeLLMConfigEventHandler() 
        )
        registry.register(
            CreateLLMInstanceEvent,
            CreateLLMInstanceEventHandler(llm_factory=self.llm_factory)
        )
        
        # Regular Processing Handlers
        registry.register(UserMessageReceivedEvent, UserInputMessageEventHandler())
        registry.register(InterAgentMessageReceivedEvent, InterAgentMessageReceivedEventHandler()) 
        registry.register(LLMCompleteResponseReceivedEvent, LLMCompleteResponseReceivedEventHandler())
        registry.register(PendingToolInvocationEvent, ToolInvocationRequestEventHandler()) 
        registry.register(ToolResultEvent, ToolResultEventHandler())
        registry.register(GenericEvent, GenericEventHandler())
        registry.register(ToolExecutionApprovalEvent, ToolExecutionApprovalEventHandler())
        registry.register(LLMUserMessageReadyEvent, LLMUserMessageReadyEventHandler()) 
        registry.register(ApprovedToolInvocationEvent, ApprovedToolInvocationEventHandler()) 
        
        # Lifecycle Logging Handlers
        lifecycle_logger_instance = LifecycleEventLogger() 
        registry.register(AgentStartedEvent, lifecycle_logger_instance) 
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
                                auto_execute_tools: bool = True # RENAMED PARAMETER
                                ) -> tuple[AgentConfig, AgentRuntimeState]:
        logger.debug(f"Creating AgentConfig for agent_id '{agent_id}' using definition '{definition.name}'. "
                     f"LLM Model Name: {llm_model_name}. Auto Execute: {auto_execute_tools}.") # UPDATED LOGGING

        if not isinstance(definition, AgentDefinition):
            raise TypeError(f"Expected AgentDefinition, got {type(definition).__name__}")
        if not llm_model_name or not isinstance(llm_model_name, str): 
            raise TypeError(f"An 'llm_model_name' (string) must be specified. Got {type(llm_model_name)}")
        if custom_llm_config is not None and not isinstance(custom_llm_config, LLMConfig): 
            raise TypeError(f"custom_llm_config must be an LLMConfig instance or None. Got {type(custom_llm_config)}")
        if custom_tool_config is not None and not (
            isinstance(custom_tool_config, dict) and
            all(isinstance(k, str) and isinstance(v, ToolConfig) for k, v in custom_tool_config.items())
        ): 
            raise TypeError("custom_tool_config must be a Dict[str, ToolConfig] or None.")
        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace):
             raise TypeError(f"Expected BaseAgentWorkspace or None for workspace, got {type(workspace).__name__}")

        agent_config = AgentConfig(
            agent_id=agent_id,
            definition=definition,
            auto_execute_tools=auto_execute_tools, # PARAMETER USED HERE
            llm_model_name=llm_model_name,
            custom_llm_config=custom_llm_config,
            custom_tool_config=custom_tool_config
        )
        logger.info(f"AgentConfig created for agent_id '{agent_id}'.")

        queues = AgentEventQueues() 
        agent_runtime_state = AgentRuntimeState(
            agent_id=agent_id, 
            queues=queues,
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
                             auto_execute_tools: bool = True # RENAMED PARAMETER
                             ) -> AgentContext: 
        agent_config, agent_runtime_state = self._create_agent_config_and_state(
            agent_id=agent_id,
            definition=definition,
            llm_model_name=llm_model_name,
            workspace=workspace,
            custom_llm_config=custom_llm_config,
            custom_tool_config=custom_tool_config,
            auto_execute_tools=auto_execute_tools # PARAMETER USED HERE
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
                             auto_execute_tools: bool = True # RENAMED PARAMETER
                             ) -> 'AgentRuntime': 
        from autobyteus.agent.agent_runtime import AgentRuntime 

        composite_agent_context = self.create_agent_context(
            agent_id=agent_id, 
            definition=definition, 
            llm_model_name=llm_model_name, 
            workspace=workspace,
            custom_llm_config=custom_llm_config, 
            custom_tool_config=custom_tool_config,
            auto_execute_tools=auto_execute_tools # PARAMETER USED HERE
        )
        
        event_handler_registry = self._get_default_event_handler_registry()
        
        tool_exec_mode_log = "Automatic" if auto_execute_tools else "Requires Approval" # UPDATED LOGGING
        logger.info(f"Instantiating AgentRuntime for agent_id: '{agent_id}' with definition: '{definition.name}'. "
                     f"LLM Model Name (for init): {llm_model_name}. Workspace: {workspace is not None}. Tool Exec Mode: {tool_exec_mode_log}")
        
        return AgentRuntime(context=composite_agent_context, event_handler_registry=event_handler_registry)

