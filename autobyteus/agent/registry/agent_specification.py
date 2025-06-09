# file: autobyteus/autobyteus/agent/registry/agent_specification.py
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class AgentSpecification:
    """
    Represents the complete, concrete specification for a single agent runtime instance.
    This is an ephemeral object created just before agent instantiation. It contains
    all necessary configuration, including the final resolved system prompt string
    and runtime flags like the tool format preference.
    """
    DEFAULT_LLM_RESPONSE_PROCESSORS = ["xml_tool_usage"] 
    DEFAULT_SYSTEM_PROMPT_PROCESSORS = ["ToolDescriptionInjector", "ToolUsageExampleInjector"]

    def __init__(self,
                 name: str,
                 role: str,
                 description: str,
                 system_prompt: str,
                 tool_names: List[str],
                 input_processor_names: Optional[List[str]] = None,
                 llm_response_processor_names: Optional[List[str]] = None,
                 system_prompt_processor_names: Optional[List[str]] = None,
                 use_xml_tool_format: bool = True):
        """
        Initializes the AgentSpecification.
        """
        self.name = name
        self.role = role
        self.description = description
        self.system_prompt = system_prompt
        self.tool_names = tool_names
        self.input_processor_names = input_processor_names or []
        self.llm_response_processor_names = llm_response_processor_names if llm_response_processor_names is not None else list(self.DEFAULT_LLM_RESPONSE_PROCESSORS)
        self.system_prompt_processor_names = system_prompt_processor_names if system_prompt_processor_names is not None else list(self.DEFAULT_SYSTEM_PROMPT_PROCESSORS)
        self.use_xml_tool_format = use_xml_tool_format

        logger.debug(f"AgentSpecification created for name '{self.name}', role '{self.role}'.")

    def __repr__(self) -> str:
        return (f"AgentSpecification(name='{self.name}', role='{self.role}', "
                f"use_xml_tool_format={self.use_xml_tool_format})")
