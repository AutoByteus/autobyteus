# file: autobyteus/autobyteus/workflow/events/workflow_events.py
from dataclasses import dataclass
from typing import Dict, Any, Optional

from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

@dataclass
class BaseWorkflowEvent:
    """Base class for all workflow events."""

@dataclass
class LifecycleWorkflowEvent(BaseWorkflowEvent):
    """Base class for events related to the workflow's lifecycle."""

@dataclass
class OperationalWorkflowEvent(BaseWorkflowEvent):
    """Base class for events related to the workflow's operational logic."""

# Specific Events
@dataclass
class WorkflowReadyEvent(LifecycleWorkflowEvent):
    """Indicates the workflow has completed bootstrapping and is ready for tasks."""

@dataclass
class WorkflowErrorEvent(LifecycleWorkflowEvent):
    """Indicates a significant error occurred within the workflow."""
    error_message: str
    exception_details: Optional[str] = None

@dataclass
class ProcessUserMessageEvent(OperationalWorkflowEvent):
    """Carries a user's message to be processed by a specific agent in the workflow."""
    user_message: AgentInputUserMessage
    target_agent_name: str

@dataclass
class InterAgentMessageRequestEvent(OperationalWorkflowEvent):
    """
    An internal request within the workflow to post a message from one agent to another.
    This triggers on-demand startup logic if needed.
    """
    sender_agent_id: str
    recipient_name: str
    content: str
    message_type: str

@dataclass
class ToolApprovalWorkflowEvent(OperationalWorkflowEvent):
    """Carries a user's approval/denial for a tool execution to a specific agent."""
    agent_name: str
    tool_invocation_id: str
    is_approved: bool
    reason: Optional[str] = None
