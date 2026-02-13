# file: autobyteus/autobyteus/agent/events/__init__.py
"""
Event definitions and event queue management for agents.
Also includes the WorkerEventDispatcher for routing events within an agent's worker loop.
"""
from .agent_input_event_queue_manager import AgentInputEventQueueManager
from .worker_event_dispatcher import WorkerEventDispatcher 
from .event_store import AgentEventStore, EventEnvelope

from .agent_events import (
    BaseEvent,
    # Categorical Base Events
    LifecycleEvent,
    AgentProcessingEvent,
    # Agent Status-Specific Base Events
    AgentOperationalEvent,
    # Specific Lifecycle Events
    AgentReadyEvent, 
    AgentStoppedEvent,
    AgentErrorEvent,
    AgentIdleEvent,
    ShutdownRequestedEvent,
    BootstrapStartedEvent,
    BootstrapStepRequestedEvent,
    BootstrapStepCompletedEvent,
    BootstrapCompletedEvent,
    # Regular Agent Processing Events
    UserMessageReceivedEvent, 
    InterAgentMessageReceivedEvent, 
    LLMUserMessageReadyEvent, 
    LLMCompleteResponseReceivedEvent,
    PendingToolInvocationEvent, 
    ToolResultEvent,
    ToolExecutionApprovalEvent,
    ExecuteToolInvocationEvent,
    # General Purpose Event
    GenericEvent
)

__all__ = [
    "AgentInputEventQueueManager", 
    "WorkerEventDispatcher", 
    "AgentEventStore",
    "EventEnvelope",
    "BaseEvent",
    "LifecycleEvent",
    "AgentProcessingEvent",
    "AgentOperationalEvent", 
    "AgentReadyEvent", 
    "AgentStoppedEvent",
    "AgentErrorEvent",
    "AgentIdleEvent",
    "ShutdownRequestedEvent",
    "BootstrapStartedEvent",
    "BootstrapStepRequestedEvent",
    "BootstrapStepCompletedEvent",
    "BootstrapCompletedEvent",
    "UserMessageReceivedEvent",
    "InterAgentMessageReceivedEvent",
    "LLMUserMessageReadyEvent", 
    "LLMCompleteResponseReceivedEvent",
    "PendingToolInvocationEvent",
    "ToolResultEvent",
    "ToolExecutionApprovalEvent",
    "ExecuteToolInvocationEvent",
    "GenericEvent",
]
