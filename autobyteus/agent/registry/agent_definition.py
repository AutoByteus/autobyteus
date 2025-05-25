# file: autobyteus/autobyteus/agent/registry/agent_definition.py
import logging
from typing import List, Dict, Any, Optional

from autobyteus.llm.models import LLMModel 
from .agent_definition_meta import AgentDefinitionMeta 

logger = logging.getLogger(__name__)

class AgentDefinition(metaclass=AgentDefinitionMeta):
    """
    Represents the static definition of an agent, containing its name, role,
    description, tools, system prompt, input processor configurations,
    LLM response processor configurations, and system prompt processor configurations.
    Instances of this class are auto-registered with the default AgentDefinitionRegistry.
    """
    DEFAULT_LLM_RESPONSE_PROCESSORS = ["xml_tool_usage"] 
    DEFAULT_SYSTEM_PROMPT_PROCESSORS = ["ToolDescriptionInjector"] # Default processor for {{tools}}

    def __init__(self,
                 name: str,
                 role: str,
                 description: str,
                 system_prompt: str,
                 tool_names: List[str],
                 input_processor_names: Optional[List[str]] = None,
                 llm_response_processor_names: Optional[List[str]] = None,
                 system_prompt_processor_names: Optional[List[str]] = None): # New attribute
        """
        Initializes the AgentDefinition.

        Args:
            name: The unique name identifier for this agent definition.
            role: A functional or descriptive role for the agent.
            description: A human-readable description of the agent's purpose.
            system_prompt: The system prompt (template) to configure the LLM's behavior.
            tool_names: A list of tool names the agent is configured to use.
            input_processor_names: Optional list of names for input message processors.
            llm_response_processor_names: Optional list of names for LLM response processors.
                                          Defaults to `DEFAULT_LLM_RESPONSE_PROCESSORS`.
            system_prompt_processor_names: Optional list of names for system prompt processors.
                                           Defaults to `DEFAULT_SYSTEM_PROMPT_PROCESSORS`.

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
        # system_prompt can now be a template, so allow it to be potentially shorter if it relies on processing
        if not isinstance(system_prompt, str): # Still must be a string
            raise ValueError(f"AgentDefinition '{name}' requires 'system_prompt' to be a string.")
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
        
        self._system_prompt_processor_names = list(self.DEFAULT_SYSTEM_PROMPT_PROCESSORS) # New logic
        if system_prompt_processor_names is not None:
            if not isinstance(system_prompt_processor_names, list) or not all(isinstance(p_name, str) for p_name in system_prompt_processor_names):
                raise ValueError(f"AgentDefinition '{name}' requires 'system_prompt_processor_names' to be a List[str] if provided.")
            self._system_prompt_processor_names = system_prompt_processor_names


        self._name = name
        self._role = role
        self._description = description
        self._system_prompt: str = system_prompt # This is now a template
        self._tool_names = tool_names

        logger.debug(f"AgentDefinition initialized for name '{self.name}', role '{self.role}', "
                     f"input_processors: {self._input_processor_names}, "
                     f"llm_response_processors: {self._llm_response_processor_names}, "
                     f"system_prompt_processors: {self._system_prompt_processor_names}.") # Added new log part

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

    @property
    def system_prompt(self) -> str:
        """The system prompt template for the agent."""
        return self._system_prompt

    @property
    def input_processor_names(self) -> List[str]:
        return self._input_processor_names

    @property
    def llm_response_processor_names(self) -> List[str]: 
        return self._llm_response_processor_names

    @property
    def system_prompt_processor_names(self) -> List[str]: # New property
        return self._system_prompt_processor_names

    def __repr__(self) -> str:
        desc_repr = self.description[:67] + "..." if len(self.description) > 70 else self.description
        desc_repr = desc_repr.replace('\n', '\\n').replace('\t', '\\t')
        
        prompt_repr = self.system_prompt[:47] + "..." if len(self.system_prompt) > 50 else self.system_prompt
        prompt_repr = prompt_repr.replace('\n', '\\n').replace('\t', '\\t')

        return (f"AgentDefinition(name='{self.name}', role='{self.role}', description='{desc_repr}', "
                f"system_prompt_template='{prompt_repr}', tool_names={self.tool_names}, "
                f"input_processor_names={self.input_processor_names}, "
                f"llm_response_processor_names={self.llm_response_processor_names}, "
                f"system_prompt_processor_names={self.system_prompt_processor_names})") # Added to repr

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "system_prompt": self.system_prompt, # This is the template
            "tool_names": self.tool_names,
            "input_processor_names": self.input_processor_names,
            "llm_response_processor_names": self.llm_response_processor_names,
            "system_prompt_processor_names": self.system_prompt_processor_names, # Added to dict
        }
