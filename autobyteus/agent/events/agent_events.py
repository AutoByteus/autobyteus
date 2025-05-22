# file: autobyteus/autobyteus/agent/events/agent_events.py
from dataclasses import dataclass, field 
from typing import Any, Dict, Optional

# Imports will need to change based on new locations
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage 
from autobyteus.agent.tool_invocation import ToolInvocation 
from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.llm.user_message import LLMUserMessage 

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


# --- Specific Lifecycle Events ---

@dataclass
class AgentStartedEvent(LifecycleEvent):
    """Event indicating the agent has started its main execution loop."""
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


@dataclass
class UserMessageReceivedEvent(AgentProcessingEvent): 
    """Event carrying an agent user message that has been received and needs initial processing."""
    agent_input_user_message: AgentInputUserMessage 

@dataclass
class InterAgentMessageReceivedEvent(AgentProcessingEvent): 
    """Event carrying an InterAgentMessage received from another agent."""
    inter_agent_message: InterAgentMessage

@dataclass
class LLMPromptReadyEvent(AgentProcessingEvent): 
    """Event indicating that an LLMUserMessage is prepared and ready for LLM processing."""
    llm_user_message: LLMUserMessage 

@dataclass
class LLMCompleteResponseReceivedEvent(AgentProcessingEvent): 
    """Event indicating that a complete LLM response has been received and aggregated."""
    complete_response_text: str
    is_error: bool = False 

@dataclass
class PendingToolInvocationEvent(AgentProcessingEvent): 
    """Event requesting a tool to be invoked, indicating it's pending execution or approval."""
    tool_invocation: ToolInvocation 

@dataclass
class ToolResultEvent(AgentProcessingEvent): 
    """Event carrying the result of a tool execution."""
    tool_name: str
    result: Any
    tool_invocation_id: Optional[str] = None 
    error: Optional[str] = None

@dataclass
class ToolExecutionApprovalEvent(AgentProcessingEvent): 
    """Event carrying the approval or denial for a tool execution request."""
    tool_invocation_id: str 
    is_approved: bool
    reason: Optional[str] = None 

@dataclass
class ApprovedToolInvocationEvent(AgentProcessingEvent):
    """Event indicating a tool invocation has been approved and is ready for execution."""
    tool_invocation: ToolInvocation


@dataclass
class GenericEvent(BaseEvent): 
    """
    A generic event for miscellaneous purposes.
    Its 'type_name' attribute can be used by a GenericEventHandler for sub-dispatch.
    """
    payload: Dict[str, Any]
    type_name: str 
