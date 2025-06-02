# file: autobyteus/autobyteus/agent/events/__init__.py
"""
Event definitions and event queue management for agents.
"""
# Removed: from .agent_event_queues import AgentEventQueues, END_OF_STREAM_SENTINEL
from .agent_input_event_queue_manager import AgentInputEventQueueManager
from .agent_output_data_manager import AgentOutputDataManager, END_OF_STREAM_SENTINEL

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
    AgentReadyEvent, # MODIFIED: Renamed from AgentStartedEvent
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
    # "AgentEventQueues", # REMOVED
    "AgentInputEventQueueManager", 
    "AgentOutputDataManager",      
    "END_OF_STREAM_SENTINEL",    
    "BaseEvent",
    "LifecycleEvent",
    "AgentProcessingEvent",
    "AgentPreparationEvent", 
    "AgentOperationalEvent", 
    "BootstrapAgentEvent", 
    "AgentReadyEvent", # MODIFIED: Renamed from AgentStartedEvent
    "AgentStoppedEvent",
    "AgentErrorEvent",
    "CreateToolInstancesEvent", # Kept for now, but deprecated in standard flow
    "ProcessSystemPromptEvent", # Kept for now, but deprecated in standard flow
    "FinalizeLLMConfigEvent",   # Kept for now, but deprecated in standard flow
    "CreateLLMInstanceEvent",   # Kept for now, but deprecated in standard flow
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
