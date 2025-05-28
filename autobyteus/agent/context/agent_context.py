# file: autobyteus/autobyteus/agent/context/agent_context.py
import logging
from typing import TYPE_CHECKING, List, Dict, Any, Optional

# Forward references for type hinting within this module
if TYPE_CHECKING:
    from .agent_config import AgentConfig 
    from .agent_runtime_state import AgentRuntimeState 
    from autobyteus.agent.registry.agent_definition import AgentDefinition
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.events.agent_event_queues import AgentEventQueues
    from autobyteus.agent.status import AgentStatus
    from autobyteus.agent.tool_invocation import ToolInvocation
    from autobyteus.llm.utils.llm_config import LLMConfig
    from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
    from autobyteus.agent.context.agent_status_manager import AgentStatusManager # For status_manager property
    from autobyteus.tools.tool_config import ToolConfig # For custom_tool_config property


logger = logging.getLogger(__name__)

class AgentContext:
    """
    Represents the complete operational context for a single agent instance,
    composed of static configuration (AgentConfig) and dynamic runtime state
    (AgentRuntimeState). Tool instances are now accessed via AgentRuntimeState.

    It serves as the primary data object passed to event handlers and used by
    the agent runtime.
    """
    def __init__(self, config: 'AgentConfig', state: 'AgentRuntimeState'):
        """
        Initializes the AgentContext.

        Args:
            config: The static configuration for the agent.
            state: The dynamic runtime state for the agent.
        """
        # Deferred imports for concrete type checking to avoid circular dependencies at module load time
        from .agent_config import AgentConfig as AgentConfigClass 
        from .agent_runtime_state import AgentRuntimeState as AgentRuntimeStateClass 

        if not isinstance(config, AgentConfigClass):
            raise TypeError(f"AgentContext 'config' must be an AgentConfig instance. Got {type(config)}")
        if not isinstance(state, AgentRuntimeStateClass):
            raise TypeError(f"AgentContext 'state' must be an AgentRuntimeState instance. Got {type(state)}")
        
        if config.agent_id != state.agent_id:
            logger.warning(f"AgentContext created with mismatched agent_id in config ('{config.agent_id}') and state ('{state.agent_id}'). Using config's ID for logging context init.")
            # state.agent_id = config.agent_id # Or raise error. Let state manage its own ID for now.

        self.config: 'AgentConfig' = config
        self.state: 'AgentRuntimeState' = state
        
        logger.info(f"AgentContext composed for agent_id '{self.config.agent_id}'. Config and State linked.")

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def definition(self) -> 'AgentDefinition':
        return self.config.definition

    @property
    def tool_instances(self) -> Dict[str, 'BaseTool']:
        """Returns the dictionary of tool instances from runtime state, or an empty dict if not yet initialized."""
        return self.state.tool_instances if self.state.tool_instances is not None else {}

    @property
    def auto_execute_tools(self) -> bool:
        return self.config.auto_execute_tools
    
    @property
    def llm_model_name(self) -> str: 
        return self.config.llm_model_name

    @property
    def custom_llm_config(self) -> Optional['LLMConfig']: 
        return self.config.custom_llm_config
    
    @property
    def custom_tool_config(self) -> Optional[Dict[str, 'ToolConfig']]: 
        """Convenience property to access custom_tool_config from AgentConfig."""
        return self.config.custom_tool_config


    @property
    def llm_instance(self) -> Optional['BaseLLM']:
        return self.state.llm_instance

    @llm_instance.setter
    def llm_instance(self, value: Optional['BaseLLM']):
        self.state.llm_instance = value

    @property
    def queues(self) -> 'AgentEventQueues':
        return self.state.queues

    @property
    def status(self) -> Optional['AgentStatus']:
        return self.state.status

    @status.setter
    def status(self, value: Optional['AgentStatus']):
        self.state.status = value

    @property
    def status_manager(self) -> Optional['AgentStatusManager']: 
        """Returns the status manager reference from runtime state."""
        return self.state.status_manager_ref


    @property
    def conversation_history(self) -> List[Dict[str, Any]]:
        return self.state.conversation_history

    @property
    def pending_tool_approvals(self) -> Dict[str, 'ToolInvocation']:
        return self.state.pending_tool_approvals

    @property
    def custom_data(self) -> Dict[str, Any]:
        return self.state.custom_data
        
    @property
    def workspace(self) -> Optional['BaseAgentWorkspace']:
        return self.state.workspace
    
    # Properties for new fields in AgentRuntimeState related to init sequence
    @property
    def processed_system_prompt(self) -> Optional[str]:
        return self.state.processed_system_prompt
    
    @processed_system_prompt.setter
    def processed_system_prompt(self, value: Optional[str]):
        self.state.processed_system_prompt = value

    @property
    def final_llm_config_for_creation(self) -> Optional['LLMConfig']:
        return self.state.final_llm_config_for_creation
        
    @final_llm_config_for_creation.setter
    def final_llm_config_for_creation(self, value: Optional['LLMConfig']):
        self.state.final_llm_config_for_creation = value

    # Methods that delegate to AgentRuntimeState or use AgentConfig

    def add_message_to_history(self, message: Dict[str, Any]) -> None:
        self.state.add_message_to_history(message)

    def get_tool(self, tool_name: str) -> Optional['BaseTool']:
        """Retrieves a tool instance from the runtime state's tool_instances."""
        # tool_instances property already handles None case by returning {}
        tool = self.tool_instances.get(tool_name) 
        if not tool:
            logger.warning(f"Tool '{tool_name}' not found in AgentContext.state.tool_instances for agent '{self.agent_id}'. "
                           f"Available tools: {list(self.tool_instances.keys())}")
        return tool

    def store_pending_tool_invocation(self, invocation: 'ToolInvocation') -> None:
        self.state.store_pending_tool_invocation(invocation)

    def retrieve_pending_tool_invocation(self, invocation_id: str) -> Optional['ToolInvocation']:
        return self.state.retrieve_pending_tool_invocation(invocation_id)

    def __repr__(self) -> str:
        return (f"AgentContext(agent_id='{self.config.agent_id}', "
                f"current_status='{self.state.status.value if self.state.status else 'None'}', "
                f"llm_initialized={self.state.llm_instance is not None}, "
                f"tools_initialized={self.state.tool_instances is not None})")

