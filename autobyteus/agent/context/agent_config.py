# file: autobyteus/autobyteus/agent/context/agent_config.py
import logging
from typing import List, Optional, Union, Tuple, TYPE_CHECKING, Dict, Any

# Correctly import the new master processor and the base class
from autobyteus.agent.system_prompt_processor import ToolManifestInjectorProcessor, BaseSystemPromptProcessor
from autobyteus.agent.llm_response_processor import ProviderAwareToolUsageProcessor, BaseLLMResponseProcessor


if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.input_processor import BaseAgentUserInputMessageProcessor
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
                 system_prompt: str,
                 tools: List['BaseTool'],
                 auto_execute_tools: bool = True,
                 use_xml_tool_format: bool = True,
                 input_processors: Optional[List['BaseAgentUserInputMessageProcessor']] = None,
                 llm_response_processors: Optional[List['BaseLLMResponseProcessor']] = None,
                 system_prompt_processors: Optional[List['BaseSystemPromptProcessor']] = None,
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
            system_prompt: The base system prompt.
            tools: A list of pre-initialized tool instances (subclasses of BaseTool).
            auto_execute_tools: If True, the agent will execute tools without approval.
            use_xml_tool_format: Whether to use XML for tool descriptions and examples.
            input_processors: A list of input processor instances.
            llm_response_processors: A list of LLM response processor instances.
            system_prompt_processors: A list of system prompt processor instances.
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
        self.tools = tools
        self.workspace = workspace
        self.auto_execute_tools = auto_execute_tools
        self.use_xml_tool_format = use_xml_tool_format
        self.input_processors = input_processors or []
        self.llm_response_processors = llm_response_processors if llm_response_processors is not None else list(self.DEFAULT_LLM_RESPONSE_PROCESSORS)
        self.system_prompt_processors = system_prompt_processors if system_prompt_processors is not None else list(self.DEFAULT_SYSTEM_PROMPT_PROCESSORS)
        self.phase_hooks = phase_hooks or []
        self.initial_custom_data = initial_custom_data

        logger.debug(f"AgentConfig created for name '{self.name}', role '{self.role}'.")

    def __repr__(self) -> str:
        return (f"AgentConfig(name='{self.name}', role='{self.role}', llm_instance='{self.llm_instance.__class__.__name__}', workspace_configured={self.workspace is not None})")
