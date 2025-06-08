# file: autobyteus/autobyteus/agent/events/__init__.py
"""
Event definitions and event queue management for agents.
Also includes the WorkerEventDispatcher for routing events within an agent's worker loop.
"""
from .agent_input_event_queue_manager import AgentInputEventQueueManager
# AgentOutputDataManager and END_OF_STREAM_SENTINEL removed
from .worker_event_dispatcher import WorkerEventDispatcher 

from .agent_events import (
    BaseEvent,
    # Categorical Base Events
    LifecycleEvent,
    AgentProcessingEvent,
    # Agent Phase-Specific Base Events
    AgentPreparationEvent, 
    AgentOperationalEvent,
    # New Bootstrap Event 
    BootstrapAgentEvent, 
    # Specific Lifecycle Events
    AgentReadyEvent, 
    AgentStoppedEvent,
    AgentErrorEvent,
    # Agent Initialization Sequence Events (DEPRECATED in standard flow, kept for potential direct use or reference)
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
    "AgentInputEventQueueManager", 
    # AgentOutputDataManager and END_OF_STREAM_SENTINEL removed from __all__   
    "WorkerEventDispatcher", 
    "BaseEvent",
    "LifecycleEvent",
    "AgentProcessingEvent",
    "AgentPreparationEvent", 
    "AgentOperationalEvent", 
    "BootstrapAgentEvent", 
    "AgentReadyEvent", 
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
