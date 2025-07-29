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
class ProcessRequestEvent(OperationalWorkflowEvent):
    """Carries a user's request to be processed by the workflow."""
    user_message: AgentInputUserMessage

@dataclass
class PostInterAgentMessageRequestEvent(OperationalWorkflowEvent):
    """
    An internal request within the workflow to post a message from one agent to another.
    This triggers on-demand startup logic if needed.
    """
    sender_agent_id: str
    recipient_name: str
    content: str
    message_type: str
