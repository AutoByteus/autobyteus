import logging
import asyncio # Added for get_running_loop
from typing import List, Union, Optional, Dict, cast, Type, TYPE_CHECKING, Any

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.registry import ToolRegistry, default_tool_registry
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig

from autobyteus.agent.context.agent_config import AgentConfig 
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState 
from autobyteus.agent.context.agent_context import AgentContext 

from autobyteus.agent.events import ( 
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent, 
    PendingToolInvocationEvent, 
    ToolResultEvent,
    LLMCompleteResponseReceivedEvent, 
    GenericEvent, 
    AgentReadyEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    ToolExecutionApprovalEvent,
    LLMUserMessageReadyEvent, 
    ApprovedToolInvocationEvent,
    BootstrapAgentEvent, 
)
from autobyteus.agent.registry.agent_specification import AgentSpecification
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
    BootstrapAgentEventHandler, 
)
from autobyteus.agent.system_prompt_processor import default_system_prompt_processor_registry, SystemPromptProcessorRegistry

if TYPE_CHECKING:
    from autobyteus.agent.runtime.agent_runtime import AgentRuntime


logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory class for creating agents.
    This factory creates AgentConfig, AgentRuntimeState, the composite AgentContext, 
    and AgentRuntime objects. AgentRuntime, in turn, creates an AgentWorker which
    initializes its own event queues via a bootstrap step.
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
        
        if system_prompt_processor_registry is not None:
            self.system_prompt_processor_registry = system_prompt_processor_registry
        else:
            self.system_prompt_processor_registry = default_system_prompt_processor_registry
        
        logger.info("AgentFactory initialized with ToolRegistry, LLMFactory, and SystemPromptProcessorRegistry.")

    def _get_default_event_handler_registry(self) -> EventHandlerRegistry:
        registry = EventHandlerRegistry()
        
        registry.register(
            BootstrapAgentEvent,
            BootstrapAgentEventHandler(
                tool_registry=self.tool_registry,
                system_prompt_processor_registry=self.system_prompt_processor_registry,
                llm_factory=self.llm_factory
            )
        )
        
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
        
        logger.debug(f"Default EventHandlerRegistry created with handlers for: {[cls.__name__ for cls in registry.get_all_registered_event_types()]}")
        return registry

    def _create_agent_config_and_state(self,
                                agent_id: str,
                                specification: AgentSpecification,
                                llm_model_name: str,
                                workspace: Optional[BaseAgentWorkspace] = None,
                                custom_llm_config: Optional[LLMConfig] = None,
                                custom_tool_config: Optional[Dict[str, ToolConfig]] = None,
                                auto_execute_tools: bool = True 
                                ) -> tuple[AgentConfig, AgentRuntimeState]:

        if not isinstance(specification, AgentSpecification):
            raise TypeError(f"Expected AgentSpecification, got {type(specification).__name__}")

        agent_config = AgentConfig(
            agent_id=agent_id,
            specification=specification,
            auto_execute_tools=auto_execute_tools, 
            llm_model_name=llm_model_name,
            custom_llm_config=custom_llm_config,
            custom_tool_config=custom_tool_config
        )
        logger.info(f"AgentConfig created for agent_id '{agent_id}'.")

        agent_runtime_state = AgentRuntimeState(
            agent_id=agent_id, 
            workspace=workspace,
        )
        logger.info(f"AgentRuntimeState created for agent_id '{agent_id}'. Event queues will be initialized by AgentWorker.")
        
        return agent_config, agent_runtime_state


    def create_agent_context(self, 
                             agent_id: str, 
                             specification: AgentSpecification, 
                             llm_model_name: str, 
                             workspace: Optional[BaseAgentWorkspace] = None,
                             custom_llm_config: Optional[LLMConfig] = None,
                             custom_tool_config: Optional[Dict[str, ToolConfig]] = None,
                             auto_execute_tools: bool = True 
                             ) -> AgentContext: 

        agent_config, agent_runtime_state = self._create_agent_config_and_state(
            agent_id=agent_id,
            specification=specification,
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
                             specification: AgentSpecification,
                             llm_model_name: str, 
                             workspace: Optional[BaseAgentWorkspace] = None,
                             custom_llm_config: Optional[LLMConfig] = None, 
                             custom_tool_config: Optional[Dict[str, ToolConfig]] = None, 
                             auto_execute_tools: bool = True 
                             ) -> 'AgentRuntime': 
        from autobyteus.agent.runtime.agent_runtime import AgentRuntime 

        composite_agent_context = self.create_agent_context(
            agent_id=agent_id, 
            specification=specification, 
            llm_model_name=llm_model_name, 
            workspace=workspace,
            custom_llm_config=custom_llm_config, 
            custom_tool_config=custom_tool_config,
            auto_execute_tools=auto_execute_tools 
        )
        
        event_handler_registry = self._get_default_event_handler_registry()
        
        tool_exec_mode_log = "Automatic" if auto_execute_tools else "Requires Approval" 
        logger.info(f"Instantiating AgentRuntime for agent_id: '{agent_id}' with spec: '{specification.name}'. "
                     f"LLM Model Name (for init): {llm_model_name}. Workspace: {workspace is not None}. Tool Exec Mode: {tool_exec_mode_log}")
        
        return AgentRuntime(
            context=composite_agent_context, 
            event_handler_registry=event_handler_registry
        )
