# file: autobyteus/autobyteus/agent/events/__init__.py
"""
Event definitions and event queue management for agents.
"""
from .agent_event_queues import AgentEventQueues, END_OF_STREAM_SENTINEL
from .agent_events import (
    BaseEvent,
    # Categorical Base Events
    LifecycleEvent,
    AgentProcessingEvent,
    # Specific Lifecycle Events
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    # Specific Agent Processing Events
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent, 
    LLMPromptReadyEvent,
    LLMCompleteResponseReceivedEvent,
    PendingToolInvocationEvent, 
    ToolResultEvent,
    ToolExecutionApprovalEvent,
    ApprovedToolInvocationEvent, # Added new event
    # General Purpose Event
    GenericEvent
)

__all__ = [
    "AgentEventQueues",
    "END_OF_STREAM_SENTINEL",
    "BaseEvent",
    "LifecycleEvent",
    "AgentProcessingEvent",
    "AgentStartedEvent",
    "AgentStoppedEvent",
    "AgentErrorEvent",
    "UserMessageReceivedEvent",
    "InterAgentMessageReceivedEvent",
    "LLMPromptReadyEvent",
    "LLMCompleteResponseReceivedEvent",
    "PendingToolInvocationEvent",
    "ToolResultEvent",
    "ToolExecutionApprovalEvent",
    "ApprovedToolInvocationEvent", # Added new event
    "GenericEvent",
]
