# file: autobyteus/autobyteus/agent/registry/agent_definition.py
import logging
from typing import List, Dict, Any, Optional

from autobyteus.llm.models import LLMModel 
from .agent_definition_meta import AgentDefinitionMeta 

logger = logging.getLogger(__name__)

class AgentDefinition(metaclass=AgentDefinitionMeta):
    """
    Represents the static definition of an agent, containing its name, role,
    description, tools, system prompt configurations, input processor configurations,
    LLM response processor configurations, system prompt processor configurations,
    and preferred tool communication format.
    Instances of this class are auto-registered with the default AgentDefinitionRegistry.
    """
    DEFAULT_LLM_RESPONSE_PROCESSORS = ["xml_tool_usage"] 
    DEFAULT_SYSTEM_PROMPT_PROCESSORS = ["ToolDescriptionInjector", "ToolUsageExampleInjector"]

    def __init__(self,
                 name: str,
                 role: str,
                 description: str,
                 default_system_prompt: str,
                 tool_names: List[str],
                 model_specific_system_prompts: Optional[Dict[str, str]] = None, # ADDED
                 input_processor_names: Optional[List[str]] = None,
                 llm_response_processor_names: Optional[List[str]] = None,
                 system_prompt_processor_names: Optional[List[str]] = None,
                 use_xml_tool_format: Optional[bool] = None):
        """
        Initializes the AgentDefinition.

        Args:
            name: The unique name identifier for this agent definition.
            role: A functional or descriptive role for the agent.
            description: A human-readable description of the agent's purpose.
            default_system_prompt: The default system prompt (template) to configure the LLM's behavior.
            tool_names: A list of tool names the agent is configured to use.
            model_specific_system_prompts: Optional. A dictionary mapping model names (from LLMModel enum)
                                           to specific system prompt templates.
            input_processor_names: Optional list of names for input message processors.
            llm_response_processor_names: Optional list of names for LLM response processors.
                                          Defaults to `DEFAULT_LLM_RESPONSE_PROCESSORS`.
            system_prompt_processor_names: Optional list of names for system prompt processors.
                                           Defaults to `DEFAULT_SYSTEM_PROMPT_PROCESSORS`.
            use_xml_tool_format: Optional boolean. If True, XML format is preferred for tool
                                 descriptions and examples. If False, JSON format is preferred.
                                 Defaults to True (XML preferred) if not specified.

        Raises:
            ValueError: If any essential parameters are invalid or if processor name lists
                        have an invalid format.
        """
        if not name or not isinstance(name, str):
            raise ValueError("AgentDefinition requires a non-empty string 'name'.")
        if not role or not isinstance(role, str):
            raise ValueError("AgentDefinition requires a non-empty string 'role'.")
        if not description or not isinstance(description, str):
            raise ValueError(f"AgentDefinition '{name}' requires a non-empty string 'description'.")
        if not isinstance(default_system_prompt, str): 
            raise ValueError(f"AgentDefinition '{name}' requires 'default_system_prompt' to be a string.")
        if model_specific_system_prompts is not None and (
            not isinstance(model_specific_system_prompts, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in model_specific_system_prompts.items())
        ):
            raise ValueError(f"AgentDefinition '{name}' requires 'model_specific_system_prompts' to be a Dict[str, str] if provided.")

        if not isinstance(tool_names, list) or not all(isinstance(t_name, str) for t_name in tool_names):
            raise ValueError(f"AgentDefinition '{name}' requires 'tool_names' to be a List[str].")

        self._input_processor_names = []
        if input_processor_names is not None:
            if not isinstance(input_processor_names, list) or not all(isinstance(p_name, str) for p_name in input_processor_names):
                raise ValueError(f"AgentDefinition '{name}' requires 'input_processor_names' to be a List[str] if provided.")
            self._input_processor_names = input_processor_names

        self._llm_response_processor_names = list(self.DEFAULT_LLM_RESPONSE_PROCESSORS)
        if llm_response_processor_names is not None: 
            if not isinstance(llm_response_processor_names, list) or not all(isinstance(p_name, str) for p_name in llm_response_processor_names): 
                raise ValueError(f"AgentDefinition '{name}' requires 'llm_response_processor_names' to be a List[str] if provided.") 
            self._llm_response_processor_names = llm_response_processor_names
        
        self._system_prompt_processor_names = list(self.DEFAULT_SYSTEM_PROMPT_PROCESSORS) 
        if system_prompt_processor_names is not None:
            if not isinstance(system_prompt_processor_names, list) or not all(isinstance(p_name, str) for p_name in system_prompt_processor_names):
                raise ValueError(f"AgentDefinition '{name}' requires 'system_prompt_processor_names' to be a List[str] if provided.")
            self._system_prompt_processor_names = system_prompt_processor_names

        if use_xml_tool_format is not None and not isinstance(use_xml_tool_format, bool):
            raise ValueError(f"AgentDefinition '{name}' requires 'use_xml_tool_format' to be a boolean if provided.")
        self._use_xml_tool_format: bool = True if use_xml_tool_format is None else use_xml_tool_format


        self._name = name
        self._role = role
        self._description = description
        self._default_system_prompt: str = default_system_prompt 
        self._model_specific_system_prompts: Dict[str, str] = model_specific_system_prompts or {}
        self._tool_names = tool_names

        logger.debug(f"AgentDefinition initialized for name '{self.name}', role '{self.role}', "
                     f"input_processors: {self._input_processor_names}, "
                     f"llm_response_processors: {self._llm_response_processor_names}, "
                     f"system_prompt_processors: {self._system_prompt_processor_names}, "
                     f"use_xml_tool_format: {self._use_xml_tool_format}, "
                     f"model_specific_prompts: {list(self._model_specific_system_prompts.keys())}.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def role(self) -> str:
        return self._role

    @property
    def description(self) -> str:
        return self._description

    @property
    def tool_names(self) -> List[str]:
        return self._tool_names

    def get_system_prompt(self, model_name: Optional[str] = None) -> str:
        """
        Retrieves the system prompt for a given model name.
        If a specific prompt for the model_name exists, it is returned.
        Otherwise, the default system prompt is returned.
        """
        if model_name and model_name in self._model_specific_system_prompts:
            logger.debug(f"Returning model-specific system prompt for model '{model_name}' for agent definition '{self.name}'.")
            return self._model_specific_system_prompts[model_name]
        
        logger.debug(f"Returning default system prompt for agent definition '{self.name}'.")
        return self._default_system_prompt

    @property
    def default_system_prompt(self) -> str:
        """The default system prompt template for the agent."""
        return self._default_system_prompt

    @property
    def model_specific_system_prompts(self) -> Dict[str, str]:
        """A dictionary of model-specific system prompts."""
        return self._model_specific_system_prompts

    @property
    def input_processor_names(self) -> List[str]:
        return self._input_processor_names

    @property
    def llm_response_processor_names(self) -> List[str]: 
        return self._llm_response_processor_names

    @property
    def system_prompt_processor_names(self) -> List[str]: 
        return self._system_prompt_processor_names

    @property
    def use_xml_tool_format(self) -> bool:
        """Determines the preferred format for tool descriptions and examples (True for XML, False for JSON)."""
        return self._use_xml_tool_format

    def __repr__(self) -> str:
        desc_repr = self.description[:67] + "..." if len(self.description) > 70 else self.description
        desc_repr = desc_repr.replace('\n', '\\n').replace('\t', '\\t')
        
        prompt_repr = self.default_system_prompt[:47] + "..." if len(self.default_system_prompt) > 50 else self.default_system_prompt
        prompt_repr = prompt_repr.replace('\n', '\\n').replace('\t', '\\t')

        return (f"AgentDefinition(name='{self.name}', role='{self.role}', description='{desc_repr}', "
                f"default_system_prompt='{prompt_repr}', model_specific_prompts={list(self.model_specific_system_prompts.keys())}, tool_names={self.tool_names}, "
                f"input_processor_names={self.input_processor_names}, "
                f"llm_response_processor_names={self.llm_response_processor_names}, "
                f"system_prompt_processor_names={self.system_prompt_processor_names}, "
                f"use_xml_tool_format={self.use_xml_tool_format})")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "default_system_prompt": self.default_system_prompt, 
            "model_specific_system_prompts": self.model_specific_system_prompts,
            "tool_names": self.tool_names,
            "input_processor_names": self.input_processor_names,
            "llm_response_processor_names": self.llm_response_processor_names,
            "system_prompt_processor_names": self.system_prompt_processor_names,
            "use_xml_tool_format": self.use_xml_tool_format,
        }
