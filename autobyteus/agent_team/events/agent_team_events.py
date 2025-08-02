# file: autobyteus/autobyteus/agent_team/events/agent_team_events.py
from dataclasses import dataclass
from typing import Dict, Any, Optional

from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

@dataclass
class BaseAgentTeamEvent:
    """Base class for all agent team events."""

@dataclass
class LifecycleAgentTeamEvent(BaseAgentTeamEvent):
    """Base class for events related to the agent team's lifecycle."""

@dataclass
class OperationalAgentTeamEvent(BaseAgentTeamEvent):
    """Base class for events related to the agent team's operational logic."""

# Specific Events
@dataclass
class AgentTeamReadyEvent(LifecycleAgentTeamEvent):
    """Indicates the agent team has completed bootstrapping and is ready for tasks."""

@dataclass
class AgentTeamErrorEvent(LifecycleAgentTeamEvent):
    """Indicates a significant error occurred within the agent team."""
    error_message: str
    exception_details: Optional[str] = None

@dataclass
class ProcessUserMessageEvent(OperationalAgentTeamEvent):
    """Carries a user's message to be processed by a specific agent in the team."""
    user_message: AgentInputUserMessage
    target_agent_name: str

@dataclass
class InterAgentMessageRequestEvent(OperationalAgentTeamEvent):
    """
    An internal request within the agent team to post a message from one agent to another.
    This triggers on-demand startup logic if needed.
    """
    sender_agent_id: str
    recipient_name: str
    content: str
    message_type: str

@dataclass
class ToolApprovalTeamEvent(OperationalAgentTeamEvent):
    """Carries a user's approval/denial for a tool execution to a specific agent."""
    agent_name: str
    tool_invocation_id: str
    is_approved: bool
    reason: Optional[str] = None
