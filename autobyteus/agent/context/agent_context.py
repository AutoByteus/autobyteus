# file: autobyteus/autobyteus/agent/context/agent_context.py
import logging
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from autobyteus.agent.phases import AgentOperationalPhase 

if TYPE_CHECKING:
    from .agent_config import AgentConfig 
    from .agent_runtime_state import AgentRuntimeState 
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.events.agent_input_event_queue_manager import AgentInputEventQueueManager 
    from autobyteus.agent.tool_invocation import ToolInvocation
    # LLMConfig no longer needed here
    from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
    from autobyteus.agent.phases import AgentPhaseManager 

logger = logging.getLogger(__name__)

class AgentContext:
    """
    Represents the complete operational context for a single agent instance.
    """
    def __init__(self, agent_id: str, config: 'AgentConfig', state: 'AgentRuntimeState'):
        from .agent_config import AgentConfig as AgentConfigClass 
        from .agent_runtime_state import AgentRuntimeState as AgentRuntimeStateClass 

        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("AgentContext requires a non-empty string 'agent_id'.")
        if not isinstance(config, AgentConfigClass):
            raise TypeError(f"AgentContext 'config' must be an AgentConfig instance. Got {type(config)}")
        if not isinstance(state, AgentRuntimeStateClass):
            raise TypeError(f"AgentContext 'state' must be an AgentRuntimeState instance. Got {type(state)}")
        
        if agent_id != state.agent_id: # pragma: no cover
            logger.warning(f"AgentContext created with mismatched agent_id ('{agent_id}') and state's ID ('{state.agent_id}'). Using context's ID for logging.")

        self.agent_id: str = agent_id
        self.config: 'AgentConfig' = config
        self.state: 'AgentRuntimeState' = state
        
        logger.info(f"AgentContext composed for agent_id '{self.agent_id}'. Config and State linked.")

    @property
    def tool_instances(self) -> Dict[str, 'BaseTool']:
        return self.state.tool_instances if self.state.tool_instances is not None else {}

    @property
    def auto_execute_tools(self) -> bool:
        return self.config.auto_execute_tools

    @property
    def llm_instance(self) -> Optional['BaseLLM']:
        return self.state.llm_instance

    @llm_instance.setter
    def llm_instance(self, value: Optional['BaseLLM']):
        self.state.llm_instance = value

    @property
    def input_event_queues(self) -> 'AgentInputEventQueueManager': 
        if self.state.input_event_queues is None:
            logger.critical(f"AgentContext for '{self.agent_id}': Attempted to access 'input_event_queues' before they were initialized by AgentWorker.")
            raise RuntimeError(f"Agent '{self.agent_id}': Input event queues have not been initialized. This typically occurs during agent bootstrapping.")
        return self.state.input_event_queues

    @property
    def current_phase(self) -> 'AgentOperationalPhase': 
        return self.state.current_phase

    @current_phase.setter
    def current_phase(self, value: 'AgentOperationalPhase'): 
        if not isinstance(value, AgentOperationalPhase): # pragma: no cover
            raise TypeError(f"current_phase must be an AgentOperationalPhase instance. Got {type(value)}")
        self.state.current_phase = value

    @property
    def phase_manager(self) -> Optional['AgentPhaseManager']: 
        return self.state.phase_manager_ref

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
    
    @property
    def processed_system_prompt(self) -> Optional[str]:
        return self.state.processed_system_prompt
    
    @processed_system_prompt.setter
    def processed_system_prompt(self, value: Optional[str]):
        self.state.processed_system_prompt = value

    # final_llm_config_for_creation property removed

    def add_message_to_history(self, message: Dict[str, Any]) -> None:
        self.state.add_message_to_history(message)

    def get_tool(self, tool_name: str) -> Optional['BaseTool']:
        tool = self.tool_instances.get(tool_name) 
        if not tool: # pragma: no cover
            logger.warning(f"Tool '{tool_name}' not found in AgentContext.state.tool_instances for agent '{self.agent_id}'. "
                           f"Available tools: {list(self.tool_instances.keys())}")
        return tool

    def store_pending_tool_invocation(self, invocation: 'ToolInvocation') -> None:
        self.state.store_pending_tool_invocation(invocation)

    def retrieve_pending_tool_invocation(self, invocation_id: str) -> Optional['ToolInvocation']:
        return self.state.retrieve_pending_tool_invocation(invocation_id)

    def __repr__(self) -> str:
        input_q_status = "Initialized" if self.state.input_event_queues is not None else "Pending Init"
        return (f"AgentContext(agent_id='{self.agent_id}', "
                f"current_phase='{self.state.current_phase.value}', " 
                f"llm_initialized={self.state.llm_instance is not None}, "
                f"tools_initialized={self.state.tool_instances is not None}, "
                f"input_queues_status='{input_q_status}')")
