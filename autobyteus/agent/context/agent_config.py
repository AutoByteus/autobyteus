# file: autobyteus/autobyteus/agent/context/agent_config.py
import logging
from typing import Dict, Optional, Any

from autobyteus.agent.registry.agent_definition import AgentDefinition
# BaseTool is no longer needed here as tool_instances are removed
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.tools.tool_config import ToolConfig # ADDED for custom_tool_config type

logger = logging.getLogger(__name__)

class AgentConfig:
    """
    Encapsulates the static configuration for an agent instance.
    This data is typically defined at agent creation and remains constant
    throughout the agent's lifecycle.
    Tool instances are now managed in AgentRuntimeState and created via events.
    This class now stores custom_tool_config to be used during tool instantiation.
    """
    def __init__(self,
                 agent_id: str,
                 definition: AgentDefinition,
                 auto_execute_tools: bool,
                 llm_model_name: str,
                 custom_llm_config: Optional[LLMConfig] = None,
                 custom_tool_config: Optional[Dict[str, ToolConfig]] = None, # ADDED
                 ):
        """
        Initializes the AgentConfig.

        Args:
            agent_id: The unique identifier for this agent instance.
            definition: The static AgentDefinition (blueprint) for this agent.
            auto_execute_tools: Runtime flag for tool execution mode.
            llm_model_name: The model name (string) to be used for LLM initialization.
            custom_llm_config: Optional LLMConfig to be used for LLM initialization.
            custom_tool_config: Optional dictionary of tool-specific configurations.
        """
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("AgentConfig requires a non-empty string 'agent_id'.")
        if not isinstance(definition, AgentDefinition):
            raise TypeError(f"AgentConfig 'definition' must be an AgentDefinition. Got {type(definition)}")
        # Validation for tool_instances removed
        if not isinstance(auto_execute_tools, bool):
            raise TypeError(f"AgentConfig 'auto_execute_tools' must be a boolean. Got {type(auto_execute_tools)}")
        if not llm_model_name or not isinstance(llm_model_name, str):
            raise ValueError("AgentConfig 'llm_model_name' must be a non-empty string.")
        if custom_llm_config is not None and not isinstance(custom_llm_config, LLMConfig):
            raise TypeError(f"AgentConfig 'custom_llm_config' must be an LLMConfig or None. Got {type(custom_llm_config)}")
        if custom_tool_config is not None and not (
            isinstance(custom_tool_config, dict) and
            all(isinstance(k, str) and isinstance(v, ToolConfig) for k, v in custom_tool_config.items())
        ):
            raise TypeError("AgentConfig 'custom_tool_config' must be a Dict[str, ToolConfig] or None.")


        self.agent_id: str = agent_id
        self.definition: AgentDefinition = definition
        # self.tool_instances: Dict[str, BaseTool] = tool_instances # REMOVED
        self.auto_execute_tools: bool = auto_execute_tools
        self.llm_model_name: str = llm_model_name
        self.custom_llm_config: Optional[LLMConfig] = custom_llm_config
        self.custom_tool_config: Optional[Dict[str, ToolConfig]] = custom_tool_config # ADDED

        logger.info(f"AgentConfig initialized for agent_id '{self.agent_id}'. Definition: '{self.definition.name}', LLM Model: '{self.llm_model_name}'.")

    def __repr__(self) -> str:
        custom_tool_config_keys = list(self.custom_tool_config.keys()) if self.custom_tool_config else []
        return (f"AgentConfig(agent_id='{self.agent_id}', definition='{self.definition.name}', "
                # f"tools={list(self.tool_instances.keys())}, " # REMOVED
                f"auto_execute={self.auto_execute_tools}, "
                f"llm_model='{self.llm_model_name}', custom_llm_config_present={self.custom_llm_config is not None}, "
                f"custom_tool_config_keys={custom_tool_config_keys})")
