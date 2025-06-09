# file: autobyteus/autobyteus/agent/context/agent_config.py
import logging
from typing import Dict, Optional, Any, List

from autobyteus.agent.registry.agent_specification import AgentSpecification
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.tools.tool_config import ToolConfig 

logger = logging.getLogger(__name__)

class AgentConfig:
    """
    Encapsulates the static configuration for an agent instance.
    This data is typically defined at agent creation and remains constant
    throughout the agent's lifecycle.
    """
    def __init__(self,
                 agent_id: str,
                 specification: AgentSpecification,
                 auto_execute_tools: bool,
                 llm_model_name: str,
                 custom_llm_config: Optional[LLMConfig] = None,
                 custom_tool_config: Optional[Dict[str, ToolConfig]] = None, 
                 ):
        """
        Initializes the AgentConfig.
        """
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("AgentConfig requires a non-empty string 'agent_id'.")
        if not isinstance(specification, AgentSpecification):
            raise TypeError(f"AgentConfig 'specification' must be an AgentSpecification. Got {type(specification)}")

        self.agent_id: str = agent_id
        self.specification: AgentSpecification = specification
        self.auto_execute_tools: bool = auto_execute_tools
        self.llm_model_name: str = llm_model_name
        self.custom_llm_config: Optional[LLMConfig] = custom_llm_config
        self.custom_tool_config: Optional[Dict[str, ToolConfig]] = custom_tool_config

        logger.info(f"AgentConfig initialized for agent_id '{self.agent_id}'. Spec: '{self.specification.name}', LLM Model: '{self.llm_model_name}'.")
    
    @property
    def name(self) -> str: return self.specification.name
    @property
    def role(self) -> str: return self.specification.role
    @property
    def description(self) -> str: return self.specification.description
    @property
    def system_prompt(self) -> str: return self.specification.system_prompt
    @property
    def tool_names(self) -> List[str]: return self.specification.tool_names
    @property
    def input_processor_names(self) -> List[str]: return self.specification.input_processor_names
    @property
    def llm_response_processor_names(self) -> List[str]: return self.specification.llm_response_processor_names
    @property
    def system_prompt_processor_names(self) -> List[str]: return self.specification.system_prompt_processor_names
    @property
    def use_xml_tool_format(self) -> bool: return self.specification.use_xml_tool_format

    def __repr__(self) -> str:
        custom_tool_config_keys = list(self.custom_tool_config.keys()) if self.custom_tool_config else []
        return (f"AgentConfig(agent_id='{self.agent_id}', spec='{self.specification.name}', "
                f"auto_execute={self.auto_execute_tools}, "
                f"llm_model='{self.llm_model_name}', custom_llm_config_present={self.custom_llm_config is not None}, "
                f"custom_tool_config_keys={custom_tool_config_keys})")
