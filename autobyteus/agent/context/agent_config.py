# file: autobyteus/autobyteus/agent/context/agent_config.py
import logging
import copy
from typing import List, Optional, Union, Tuple, TYPE_CHECKING, Dict, Any

# Correctly import the new master processor and the base class
from autobyteus.agent.system_prompt_processor import ToolManifestInjectorProcessor, BaseSystemPromptProcessor
from autobyteus.agent.llm_response_processor import ProviderAwareToolUsageProcessor, BaseLLMResponseProcessor


if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.input_processor import BaseAgentUserInputMessageProcessor
    from autobyteus.agent.tool_execution_result_processor import BaseToolExecutionResultProcessor
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
    from autobyteus.agent.hooks.base_phase_hook import BasePhaseHook

logger = logging.getLogger(__name__)

class AgentConfig:
    """
    Represents the complete, static configuration for an agent instance.
    This is the single source of truth for an agent's definition, including
    its identity, capabilities, and default behaviors.
    """
    # Use the new ProviderAwareToolUsageProcessor as the default
    DEFAULT_LLM_RESPONSE_PROCESSORS = [ProviderAwareToolUsageProcessor()]
    # Use the new, single, unified processor as the default
    DEFAULT_SYSTEM_PROMPT_PROCESSORS = [ToolManifestInjectorProcessor()]

    def __init__(self,
                 name: str,
                 role: str,
                 description: str,
                 llm_instance: 'BaseLLM',
                 system_prompt: Optional[str] = None,
                 tools: Optional[List['BaseTool']] = None,
                 auto_execute_tools: bool = True,
                 use_xml_tool_format: bool = False,
                 input_processors: Optional[List['BaseAgentUserInputMessageProcessor']] = None,
                 llm_response_processors: Optional[List['BaseLLMResponseProcessor']] = None,
                 system_prompt_processors: Optional[List['BaseSystemPromptProcessor']] = None,
                 tool_execution_result_processors: Optional[List['BaseToolExecutionResultProcessor']] = None,
                 workspace: Optional['BaseAgentWorkspace'] = None,
                 phase_hooks: Optional[List['BasePhaseHook']] = None,
                 initial_custom_data: Optional[Dict[str, Any]] = None):
        """
        Initializes the AgentConfig.

        Args:
            name: The agent's name.
            role: The agent's role.
            description: A description of the agent.
            llm_instance: A pre-initialized LLM instance (subclass of BaseLLM).
                          The user is responsible for creating and configuring this instance.
            system_prompt: The base system prompt. If None, the system_message from the
                           llm_instance's config will be used as the base.
            tools: An optional list of pre-initialized tool instances (subclasses of BaseTool).
            auto_execute_tools: If True, the agent will execute tools without approval.
            use_xml_tool_format: If True, forces the agent to use XML format for tool
                                 definitions and parsing, overriding provider defaults.
            input_processors: A list of input processor instances.
            llm_response_processors: A list of LLM response processor instances.
            system_prompt_processors: A list of system prompt processor instances.
            tool_execution_result_processors: A list of tool execution result processor instances.
            workspace: An optional pre-initialized workspace instance for the agent.
            phase_hooks: An optional list of phase transition hook instances.
            initial_custom_data: An optional dictionary of data to pre-populate
                                 the agent's runtime state `custom_data`.
        """
        self.name = name
        self.role = role
        self.description = description
        self.llm_instance = llm_instance
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.workspace = workspace
        self.auto_execute_tools = auto_execute_tools
        self.use_xml_tool_format = use_xml_tool_format
        self.input_processors = input_processors or []
        self.llm_response_processors = llm_response_processors if llm_response_processors is not None else list(self.DEFAULT_LLM_RESPONSE_PROCESSORS)
        self.system_prompt_processors = system_prompt_processors if system_prompt_processors is not None else list(self.DEFAULT_SYSTEM_PROMPT_PROCESSORS)
        self.tool_execution_result_processors = tool_execution_result_processors or []
        self.phase_hooks = phase_hooks or []
        self.initial_custom_data = initial_custom_data

        logger.debug(f"AgentConfig created for name '{self.name}', role '{self.role}'. XML tool format override: {self.use_xml_tool_format}")

    def copy(self) -> 'AgentConfig':
        """
        Creates a copy of this AgentConfig. It avoids deep-copying complex objects
        like tools, workspaces, and processors that may contain un-pickleable state.
        Instead, it creates shallow copies of the lists, allowing the lists themselves
        to be modified independently while sharing the object instances within them.
        """
        return AgentConfig(
            name=self.name,
            role=self.role,
            description=self.description,
            llm_instance=self.llm_instance,  # Keep reference, do not copy
            system_prompt=self.system_prompt,
            tools=self.tools.copy(),  # Shallow copy the list, but reference the original tool instances
            auto_execute_tools=self.auto_execute_tools,
            use_xml_tool_format=self.use_xml_tool_format,
            input_processors=self.input_processors.copy(), # Shallow copy the list
            llm_response_processors=self.llm_response_processors.copy(), # Shallow copy the list
            system_prompt_processors=self.system_prompt_processors.copy(), # Shallow copy the list
            tool_execution_result_processors=self.tool_execution_result_processors.copy(), # Shallow copy the list
            workspace=self.workspace,  # Pass by reference, do not copy
            phase_hooks=self.phase_hooks.copy(), # Shallow copy the list
            initial_custom_data=copy.deepcopy(self.initial_custom_data) # Deep copy for simple data
        )

    def __repr__(self) -> str:
        return (f"AgentConfig(name='{self.name}', role='{self.role}', llm_instance='{self.llm_instance.__class__.__name__}', workspace_configured={self.workspace is not None})")
