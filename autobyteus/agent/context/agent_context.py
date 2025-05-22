# file: autobyteus/autobyteus/agent/context/agent_context.py
import logging
from typing import List, Dict, Any, Optional

# Imports will need to change based on new locations
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.events.agent_event_queues import AgentEventQueues # MODIFIED IMPORT
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.status import AgentStatus
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace 
from autobyteus.agent.tool_invocation import ToolInvocation # Added for type hinting

logger = logging.getLogger(__name__)

class AgentContext:
    """
    Represents the complete operational context for a single agent instance.
    It serves as a central data object for event handlers and the agent runtime.

    The AgentContext encapsulates:
    1.  A reference to the agent's static blueprint (`definition: AgentDefinition`).
    2.  Instantiated operational components:
        - LLM instance (`llm_instance`)
        - Tool instances (`tool_instances`)
        - Communication channels (`queues`)
        - Workspace (`workspace`)
    3.  Dynamic, instance-specific runtime state and configuration:
        - Current operational status (`status`), managed externally by AgentStatusManager.
        - Conversation history (`conversation_history`).
        - Mode for tool execution (`auto_execute_tools` - True for automatic, False for approval-based).
        - Pending tool approvals (`pending_tool_approvals`).
        - Other custom data (`custom_data`).
    
    While it holds a reference to the static AgentDefinition, the AgentContext itself
    is primarily concerned with the live, operational aspects of an agent instance.
    """
    def __init__(self,
                 agent_id: str,
                 definition: AgentDefinition,
                 queues: AgentEventQueues,
                 llm_instance: BaseLLM,
                 tool_instances: Dict[str, BaseTool],
                 auto_execute_tools: bool, 
                 workspace: Optional[BaseAgentWorkspace] = None, 
                 conversation_history: Optional[List[Dict[str, Any]]] = None,
                 custom_data: Optional[Dict[str, Any]] = None):
        """
        Initializes the AgentContext.

        Args:
            agent_id: The unique identifier for this agent instance.
            definition: The static AgentDefinition (blueprint) for this agent.
            queues: The AgentEventQueues instance for this agent's communication.
            llm_instance: The instantiated LLM model for this agent.
            tool_instances: A dictionary of instantiated tools, keyed by tool name.
            auto_execute_tools: Runtime flag. If True, tools are executed automatically.
                                If False, tools require approval.
            workspace: Optional. The agent's dedicated workspace environment.
            conversation_history: Optional pre-filled conversation history.
            custom_data: Optional dictionary for storing any other contextual data.
        """
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("AgentContext requires a non-empty string 'agent_id'.")
        
        if not isinstance(definition, AgentDefinition): # Ensure definition is correct type
            raise TypeError(f"AgentContext 'definition' must be an AgentDefinition instance. Got {type(definition)}")

        if not isinstance(queues, AgentEventQueues):
            raise TypeError(f"AgentContext 'queues' must be an AgentEventQueues instance. Got {type(queues)}")

        if not isinstance(llm_instance, BaseLLM):
            raise TypeError(f"AgentContext 'llm_instance' must be a BaseLLM instance. Got {type(llm_instance)}")
        
        if not isinstance(tool_instances, dict) or not all(isinstance(k, str) and isinstance(v, BaseTool) for k, v in tool_instances.items()):
            raise ValueError("AgentContext 'tool_instances' must be a Dict[str, BaseTool].")
        
        if workspace is not None and not isinstance(workspace, BaseAgentWorkspace):
            raise TypeError(f"AgentContext 'workspace' must be an instance of BaseAgentWorkspace or None. Got {type(workspace)}")
        
        if not isinstance(auto_execute_tools, bool): 
            raise TypeError(f"AgentContext 'auto_execute_tools' must be a boolean. Got {type(auto_execute_tools)}")

        # Core Identifiers and Static Blueprint Reference
        self.agent_id: str = agent_id
        self.definition: AgentDefinition = definition 

        # Instantiated Operational Components
        self.queues: AgentEventQueues = queues 
        self.llm_instance: BaseLLM = llm_instance
        self.tool_instances: Dict[str, BaseTool] = tool_instances
        self.workspace: Optional[BaseAgentWorkspace] = workspace 
        
        # Dynamic Runtime State and Configuration for this Instance
        self.auto_execute_tools: bool = auto_execute_tools 
        self.status: Optional[AgentStatus] = None # Initialized to None, set by AgentStatusManager
        self.conversation_history: List[Dict[str, Any]] = conversation_history or []
        self.pending_tool_approvals: Dict[str, ToolInvocation] = {} # For tool approval workflow
        self.custom_data: Dict[str, Any] = custom_data or {}


        workspace_info = f"workspace_id='{self.workspace.workspace_id}'" if self.workspace else "no workspace"
        initial_status_log = self.status.value if self.status else "None (to be set by StatusManager)"
        tool_execution_mode_log = "Automatic" if self.auto_execute_tools else "Requires Approval"
        logger.info(f"AgentContext initialized for agent_id '{self.agent_id}' with definition_name '{self.definition.name}'. "
                    f"Initial status: {initial_status_log}. Workspace: {workspace_info}. Tool Execution Mode: {tool_execution_mode_log}")
        logger.debug(f"AgentContext tools: {list(self.tool_instances.keys())}")

    def add_message_to_history(self, message: Dict[str, Any]) -> None:
        """
        Adds a message to the agent's conversation history.
        The message should typically conform to a standard structure, e.g.,
        `{"role": "user/assistant/tool", "content": "..."}`.

        Args:
            message: The message dictionary to add.
        """
        if not isinstance(message, dict) or "role" not in message: # Content can be None for tool_calls
            logger.warning(f"Attempted to add malformed message to history for agent '{self.agent_id}': {message} (missing 'role')")
            return
            
        self.conversation_history.append(message)
        logger.debug(f"Message added to history for agent '{self.agent_id}': role={message['role']}")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Retrieves an instantiated tool by its name.

        Args:
            tool_name: The name of the tool to retrieve.

        Returns:
            The BaseTool instance if found, otherwise None.
        """
        tool = self.tool_instances.get(tool_name)
        if not tool:
            logger.warning(f"Tool '{tool_name}' not found in AgentContext for agent '{self.agent_id}'. "
                           f"Available tools: {list(self.tool_instances.keys())}")
        return tool

    def store_pending_tool_invocation(self, invocation: ToolInvocation) -> None:
        """
        Stores a tool invocation that is pending approval.

        Args:
            invocation: The ToolInvocation object to store.
        """
        if not isinstance(invocation, ToolInvocation) or not invocation.id:
            logger.error(f"Agent '{self.agent_id}': Attempted to store invalid ToolInvocation for approval: {invocation}")
            return
        self.pending_tool_approvals[invocation.id] = invocation
        logger.info(f"Agent '{self.agent_id}': Stored pending tool invocation '{invocation.id}' ({invocation.name}) for approval.")

    def retrieve_pending_tool_invocation(self, invocation_id: str) -> Optional[ToolInvocation]:
        """
        Retrieves and removes a pending tool invocation by its ID.

        Args:
            invocation_id: The ID of the tool invocation to retrieve.

        Returns:
            The ToolInvocation object if found, otherwise None.
        """
        if not isinstance(invocation_id, str):
            logger.warning(f"Agent '{self.agent_id}': Attempted to retrieve pending tool invocation with non-string ID: {invocation_id}")
            return None
            
        invocation = self.pending_tool_approvals.pop(invocation_id, None)
        if invocation:
            logger.info(f"Agent '{self.agent_id}': Retrieved and removed pending tool invocation '{invocation_id}' ({invocation.name}).")
        else:
            logger.warning(f"Agent '{self.agent_id}': Pending tool invocation '{invocation_id}' not found for retrieval.")
        return invocation

    def __repr__(self) -> str:
        workspace_repr = f", workspace_id='{self.workspace.workspace_id}'" if self.workspace else ""
        status_repr = self.status.value if self.status else "None"
        tool_exec_mode = "Auto" if self.auto_execute_tools else "ApprovalReq"
        return (f"AgentContext(agent_id='{self.agent_id}', definition_name='{self.definition.name}', "
                f"status='{status_repr}', tools={list(self.tool_instances.keys())}{workspace_repr}, "
                f"tool_exec_mode='{tool_exec_mode}', "
                f"pending_approvals_count={len(self.pending_tool_approvals)})")
