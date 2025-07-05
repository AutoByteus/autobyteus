# file: autobyteus/autobyteus/agent/events/agent_events.py
from dataclasses import dataclass, field 
from typing import Any, Dict, Optional

from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage 
from autobyteus.agent.tool_invocation import ToolInvocation 
from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.llm.user_message import LLMUserMessage 
from autobyteus.llm.utils.response_types import CompleteResponse

@dataclass
class BaseEvent:
    """Base class for all agent events. Events are pure data containers."""


# --- Categorical Base Events ---

@dataclass
class LifecycleEvent(BaseEvent):
    """Base class for events related to the agent's lifecycle (e.g., start, stop, status changes, errors)."""


@dataclass
class AgentProcessingEvent(BaseEvent):
    """Base class for events related to the agent's internal data processing and task execution logic."""


# --- Agent Operational Phase Events ---
@dataclass
class AgentOperationalEvent(AgentProcessingEvent): 
    """Base class for events that occur during the agent's active operational phase (post-preparation)."""
    pass


# --- Specific Lifecycle Events ---

@dataclass
class AgentReadyEvent(LifecycleEvent):
    """Event indicating the agent has completed its bootstrapping process, is fully initialized, and is ready to process messages."""
    pass

@dataclass
class AgentStoppedEvent(LifecycleEvent):
    """Event indicating the agent has stopped its main execution loop."""
    pass

@dataclass
class AgentErrorEvent(LifecycleEvent):
    """Event indicating a significant error occurred within the agent's operation."""
    error_message: str
    exception_details: Optional[str] = None 


# --- Regular Agent Processing Events (now Operational) ---

@dataclass
class UserMessageReceivedEvent(AgentOperationalEvent): 
    """Event carrying an agent user message that has been received and needs initial processing."""
    agent_input_user_message: AgentInputUserMessage 

@dataclass
class InterAgentMessageReceivedEvent(AgentOperationalEvent): 
    """Event carrying an InterAgentMessage received from another agent."""
    inter_agent_message: InterAgentMessage

@dataclass
class LLMUserMessageReadyEvent(AgentOperationalEvent): 
    """Event indicating that an LLMUserMessage (derived from user/agent input) is prepared and ready for LLM processing."""
    llm_user_message: LLMUserMessage 

@dataclass
class LLMCompleteResponseReceivedEvent(AgentOperationalEvent): 
    """Event indicating that a complete LLM response has been received and aggregated."""
    complete_response: CompleteResponse
    is_error: bool = False 

@dataclass
class PendingToolInvocationEvent(AgentOperationalEvent): 
    """Event requesting a tool to be invoked, indicating it's pending execution or approval."""
    tool_invocation: ToolInvocation 

@dataclass
class ToolResultEvent(AgentOperationalEvent): 
    """Event carrying the result of a tool execution."""
    tool_name: str
    result: Any
    tool_invocation_id: Optional[str] = None 
    error: Optional[str] = None

@dataclass
class ToolExecutionApprovalEvent(AgentOperationalEvent): 
    """Event carrying the approval or denial for a tool execution request."""
    tool_invocation_id: str 
    is_approved: bool
    reason: Optional[str] = None 

@dataclass
class ApprovedToolInvocationEvent(AgentOperationalEvent):
    """Event indicating a tool invocation has been approved and is ready for execution."""
    tool_invocation: ToolInvocation


@dataclass
class GenericEvent(AgentOperationalEvent): 
    """
    A generic event for miscellaneous purposes, typically during active operation.
    Its 'type_name' attribute can be used by a GenericEventHandler for sub-dispatch.
    """
    payload: Dict[str, Any]
    type_name: str
