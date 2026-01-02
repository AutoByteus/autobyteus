# file: autobyteus/autobyteus/agent/context/agent_config.py
import logging
import copy
from typing import List, Optional, Union, Tuple, TYPE_CHECKING, Dict, Any

# Correctly import the new master processor and the base class
from autobyteus.agent.system_prompt_processor import ToolManifestInjectorProcessor, BaseSystemPromptProcessor, AvailableSkillsProcessor
from autobyteus.agent.llm_response_processor import BaseLLMResponseProcessor
from autobyteus.utils.tool_call_format import resolve_tool_call_format


if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.input_processor import BaseAgentUserInputMessageProcessor
    from autobyteus.agent.tool_execution_result_processor import BaseToolExecutionResultProcessor
    from autobyteus.agent.tool_invocation_preprocessor import BaseToolInvocationPreprocessor
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
    from autobyteus.agent.lifecycle import BaseLifecycleEventProcessor

logger = logging.getLogger(__name__)

class AgentConfig:
    """
    Represents the complete, static configuration for an agent instance.
    This is the single source of truth for an agent's definition, including
    its identity, capabilities, and default behaviors.
    """
    # Default to no LLM response processors; tool parsing happens during streaming.
    DEFAULT_LLM_RESPONSE_PROCESSORS: List['BaseLLMResponseProcessor'] = []
    # Use the new, single, unified processor as the default
    DEFAULT_SYSTEM_PROMPT_PROCESSORS = [ToolManifestInjectorProcessor(), AvailableSkillsProcessor()]

    def __init__(self,
                 name: str,
                 role: str,
                 description: str,
                 llm_instance: 'BaseLLM',
                 system_prompt: Optional[str] = None,
                 tools: Optional[List['BaseTool']] = None,
                 auto_execute_tools: bool = True,
                 input_processors: Optional[List['BaseAgentUserInputMessageProcessor']] = None,
                 llm_response_processors: Optional[List['BaseLLMResponseProcessor']] = None,
                 system_prompt_processors: Optional[List['BaseSystemPromptProcessor']] = None,
                 tool_execution_result_processors: Optional[List['BaseToolExecutionResultProcessor']] = None,
                 tool_invocation_preprocessors: Optional[List['BaseToolInvocationPreprocessor']] = None,
                 workspace: Optional['BaseAgentWorkspace'] = None,
                 lifecycle_processors: Optional[List['BaseLifecycleEventProcessor']] = None,
                 initial_custom_data: Optional[Dict[str, Any]] = None,
                 skills: Optional[List[str]] = None):
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
            input_processors: A list of input processor instances.
            llm_response_processors: A list of LLM response processor instances.
            system_prompt_processors: A list of system prompt processor instances.
            tool_execution_result_processors: A list of tool execution result processor instances.
            workspace: An optional pre-initialized workspace instance for the agent.
            lifecycle_processors: An optional list of lifecycle processor instances.
            initial_custom_data: An optional dictionary of data to pre-populate
                                 the agent's runtime state `custom_data`.
            skills: An optional list of skill names or paths to be preloaded for this agent.
        """
        self.name = name
        self.role = role
        self.description = description
        self.llm_instance = llm_instance
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.workspace = workspace
        self.auto_execute_tools = auto_execute_tools
        self.tool_call_format = resolve_tool_call_format()
        self.input_processors = input_processors or []
        self.llm_response_processors = llm_response_processors if llm_response_processors is not None else list(self.DEFAULT_LLM_RESPONSE_PROCESSORS)
        self.system_prompt_processors = system_prompt_processors if system_prompt_processors is not None else list(self.DEFAULT_SYSTEM_PROMPT_PROCESSORS)
        self.tool_execution_result_processors = tool_execution_result_processors or []
        self.tool_invocation_preprocessors = tool_invocation_preprocessors or []
        self.lifecycle_processors = lifecycle_processors or []
        self.initial_custom_data = initial_custom_data
        self.skills = skills or []

        logger.debug(
            "AgentConfig created for name '%s', role '%s'. Tool call format: %s",
            self.name,
            self.role,
            self.tool_call_format,
        )

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
            input_processors=self.input_processors.copy(), # Shallow copy the list
            llm_response_processors=self.llm_response_processors.copy(), # Shallow copy the list
            system_prompt_processors=self.system_prompt_processors.copy(), # Shallow copy the list
            tool_execution_result_processors=self.tool_execution_result_processors.copy(), # Shallow copy the list
            tool_invocation_preprocessors=self.tool_invocation_preprocessors.copy(),
            workspace=self.workspace,  # Pass by reference, do not copy
            lifecycle_processors=self.lifecycle_processors.copy(), # Shallow copy the list
            initial_custom_data=copy.deepcopy(self.initial_custom_data), # Deep copy for simple data
            skills=self.skills.copy() # Shallow copy the list
        )

    def __repr__(self) -> str:
        return (f"AgentConfig(name='{self.name}', role='{self.role}', llm_instance='{self.llm_instance.__class__.__name__}', workspace_configured={self.workspace is not None}, skills={self.skills})")
