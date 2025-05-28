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
    # Agent Phase-Specific Base Events
    AgentPreparationEvent, 
    AgentOperationalEvent, # NEW
    # Specific Lifecycle Events
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    # Agent Initialization Sequence Events (inheriting from AgentPreparationEvent)
    CreateToolInstancesEvent, 
    ProcessSystemPromptEvent,
    FinalizeLLMConfigEvent,
    CreateLLMInstanceEvent,
    # Regular Agent Processing Events (now inheriting from AgentOperationalEvent)
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent, 
    LLMUserMessageReadyEvent, 
    LLMCompleteResponseReceivedEvent,
    PendingToolInvocationEvent, 
    ToolResultEvent,
    ToolExecutionApprovalEvent,
    ApprovedToolInvocationEvent,
    # General Purpose Event (now inheriting from AgentOperationalEvent)
    GenericEvent
)

__all__ = [
    "AgentEventQueues",
    "END_OF_STREAM_SENTINEL",
    "BaseEvent",
    "LifecycleEvent",
    "AgentProcessingEvent",
    "AgentPreparationEvent", 
    "AgentOperationalEvent", # NEW
    "AgentStartedEvent",
    "AgentStoppedEvent",
    "AgentErrorEvent",
    "CreateToolInstancesEvent", 
    "ProcessSystemPromptEvent",
    "FinalizeLLMConfigEvent",
    "CreateLLMInstanceEvent",
    "UserMessageReceivedEvent",
    "InterAgentMessageReceivedEvent",
    "LLMUserMessageReadyEvent", 
    "LLMCompleteResponseReceivedEvent",
    "PendingToolInvocationEvent",
    "ToolResultEvent",
    "ToolExecutionApprovalEvent",
    "ApprovedToolInvocationEvent",
    "GenericEvent",
]
