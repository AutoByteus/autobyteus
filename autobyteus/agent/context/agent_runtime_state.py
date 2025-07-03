# file: autobyteus/autobyteus/agent/context/agent_runtime_state.py
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from autobyteus.agent.events.agent_input_event_queue_manager import AgentInputEventQueueManager 
# AgentOutputDataManager is no longer part of AgentRuntimeState
# from autobyteus.agent.events.agent_output_data_manager import AgentOutputDataManager       

from autobyteus.llm.base_llm import BaseLLM
from autobyteus.agent.phases import AgentOperationalPhase 
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.tool_invocation import ToolInvocation
# LLMConfig is no longer needed here
# from autobyteus.llm.utils.llm_config import LLMConfig 

if TYPE_CHECKING:
    from autobyteus.agent.phases import AgentPhaseManager 
    from autobyteus.tools.base_tool import BaseTool 

logger = logging.getLogger(__name__)

class AgentRuntimeState:
    """
    Encapsulates the dynamic, stateful data of an agent instance.
    Input event queues are initialized by the AgentWorker via a bootstrap step.
    Output data is now handled by emitting events via AgentExternalEventNotifier.
    """
    def __init__(self,
                 agent_id: str, 
                 workspace: Optional[BaseAgentWorkspace] = None,
                 conversation_history: Optional[List[Dict[str, Any]]] = None,
                 custom_data: Optional[Dict[str, Any]] = None):
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("AgentRuntimeState requires a non-empty string 'agent_id'.")
        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace): # pragma: no cover
            raise TypeError(f"AgentRuntimeState 'workspace' must be a BaseAgentWorkspace or None. Got {type(workspace)}")

        self.agent_id: str = agent_id 
        self.current_phase: AgentOperationalPhase = AgentOperationalPhase.UNINITIALIZED 
        self.llm_instance: Optional[BaseLLM] = None  
        self.tool_instances: Optional[Dict[str, 'BaseTool']] = None 
        
        self.input_event_queues: Optional[AgentInputEventQueueManager] = None 
        # REMOVED: self.output_data_queues attribute
        
        self.workspace: Optional[BaseAgentWorkspace] = workspace
        self.conversation_history: List[Dict[str, Any]] = conversation_history or []
        self.pending_tool_approvals: Dict[str, ToolInvocation] = {}
        self.custom_data: Dict[str, Any] = custom_data or {}
        
        self.processed_system_prompt: Optional[str] = None
        # self.final_llm_config_for_creation removed
        
        self.phase_manager_ref: Optional['AgentPhaseManager'] = None 
         
        logger.info(f"AgentRuntimeState initialized for agent_id '{self.agent_id}'. Initial phase: {self.current_phase.value}. Workspace linked. InputQueues pending initialization. Output data via notifier.")

    def add_message_to_history(self, message: Dict[str, Any]) -> None:
        if not isinstance(message, dict) or "role" not in message: # pragma: no cover
            logger.warning(f"Attempted to add malformed message to history for agent '{self.agent_id}': {message}")
            return
        self.conversation_history.append(message)
        logger.debug(f"Message added to history for agent '{self.agent_id}': role={message['role']}")

    def store_pending_tool_invocation(self, invocation: ToolInvocation) -> None:
        if not isinstance(invocation, ToolInvocation) or not invocation.id: # pragma: no cover
            logger.error(f"Agent '{self.agent_id}': Attempted to store invalid ToolInvocation for approval: {invocation}")
            return
        self.pending_tool_approvals[invocation.id] = invocation
        logger.info(f"Agent '{self.agent_id}': Stored pending tool invocation '{invocation.id}' ({invocation.name}).")

    def retrieve_pending_tool_invocation(self, invocation_id: str) -> Optional[ToolInvocation]:
        invocation = self.pending_tool_approvals.pop(invocation_id, None)
        if invocation:
            logger.info(f"Agent '{self.agent_id}': Retrieved pending tool invocation '{invocation_id}' ({invocation.name}).")
        else: # pragma: no cover
            logger.warning(f"Agent '{self.agent_id}': Pending tool invocation '{invocation_id}' not found.")
        return invocation
    
    def __repr__(self) -> str:
        phase_repr = self.current_phase.value
        llm_status = "Initialized" if self.llm_instance else "Not Initialized"
        tools_status = f"{len(self.tool_instances)} Initialized" if self.tool_instances is not None else "Not Initialized"
        input_queues_status = "Initialized" if self.input_event_queues else "Not Initialized"
        # REMOVED output_queues_status from repr
        return (f"AgentRuntimeState(agent_id='{self.agent_id}', current_phase='{phase_repr}', "
                f"llm_status='{llm_status}', tools_status='{tools_status}', "
                f"input_queues_status='{input_queues_status}', "
                f"pending_approvals={len(self.pending_tool_approvals)}, history_len={len(self.conversation_history)})")
