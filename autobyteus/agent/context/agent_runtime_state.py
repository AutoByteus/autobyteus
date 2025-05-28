# file: autobyteus/autobyteus/agent/context/agent_runtime_state.py
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from autobyteus.agent.events.agent_event_queues import AgentEventQueues
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.agent.status import AgentStatus
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.llm_config import LLMConfig 

if TYPE_CHECKING:
    from .agent_status_manager import AgentStatusManager 
    from autobyteus.tools.base_tool import BaseTool # ADDED for tool_instances type hint

logger = logging.getLogger(__name__)

class AgentRuntimeState:
    """
    Encapsulates the dynamic, stateful data of an agent instance.
    This data changes or is populated during the agent's lifecycle.
    Tool instances are now part of runtime state.
    """
    def __init__(self,
                 agent_id: str, 
                 queues: AgentEventQueues,
                 workspace: Optional[BaseAgentWorkspace] = None,
                 conversation_history: Optional[List[Dict[str, Any]]] = None,
                 custom_data: Optional[Dict[str, Any]] = None):
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("AgentRuntimeState requires a non-empty string 'agent_id'.")
        if not isinstance(queues, AgentEventQueues):
            raise TypeError(f"AgentRuntimeState 'queues' must be an AgentEventQueues. Got {type(queues)}")
        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace):
            raise TypeError(f"AgentRuntimeState 'workspace' must be a BaseAgentWorkspace or None. Got {type(workspace)}")

        self.agent_id: str = agent_id 
        self.status: Optional[AgentStatus] = None  
        self.llm_instance: Optional[BaseLLM] = None  
        self.tool_instances: Optional[Dict[str, 'BaseTool']] = None # ADDED: Tools are now runtime state, initialized to None
        self.queues: AgentEventQueues = queues
        self.workspace: Optional[BaseAgentWorkspace] = workspace
        self.conversation_history: List[Dict[str, Any]] = conversation_history or []
        self.pending_tool_approvals: Dict[str, ToolInvocation] = {}
        self.custom_data: Dict[str, Any] = custom_data or {}
        
        self.processed_system_prompt: Optional[str] = None
        self.final_llm_config_for_creation: Optional[LLMConfig] = None
        
        self.status_manager_ref: Optional['AgentStatusManager'] = None # Retained for ToolInvocationRequestEventHandler
         
        logger.info(f"AgentRuntimeState initialized for agent_id '{self.agent_id}'. LLM: None (initially), Tools: None (initially), Queues, Workspace linked.")

    def add_message_to_history(self, message: Dict[str, Any]) -> None:
        if not isinstance(message, dict) or "role" not in message:
            logger.warning(f"Attempted to add malformed message to history for agent '{self.agent_id}': {message}")
            return
        self.conversation_history.append(message)
        logger.debug(f"Message added to history for agent '{self.agent_id}': role={message['role']}")

    def store_pending_tool_invocation(self, invocation: ToolInvocation) -> None:
        if not isinstance(invocation, ToolInvocation) or not invocation.id:
            logger.error(f"Agent '{self.agent_id}': Attempted to store invalid ToolInvocation for approval: {invocation}")
            return
        self.pending_tool_approvals[invocation.id] = invocation
        logger.info(f"Agent '{self.agent_id}': Stored pending tool invocation '{invocation.id}' ({invocation.name}).")

    def retrieve_pending_tool_invocation(self, invocation_id: str) -> Optional[ToolInvocation]:
        invocation = self.pending_tool_approvals.pop(invocation_id, None)
        if invocation:
            logger.info(f"Agent '{self.agent_id}': Retrieved pending tool invocation '{invocation_id}' ({invocation.name}).")
        else:
            logger.warning(f"Agent '{self.agent_id}': Pending tool invocation '{invocation_id}' not found.")
        return invocation
    
    def __repr__(self) -> str:
        status_repr = self.status.value if self.status else "None"
        llm_status = "Initialized" if self.llm_instance else "Not Initialized"
        tools_status = f"{len(self.tool_instances)} Initialized" if self.tool_instances is not None else "Not Initialized"
        return (f"AgentRuntimeState(agent_id='{self.agent_id}', status='{status_repr}', "
                f"llm_status='{llm_status}', tools_status='{tools_status}', "
                f"pending_approvals={len(self.pending_tool_approvals)}, history_len={len(self.conversation_history)})")

