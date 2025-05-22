# File: autobyteus/events/event_types.py

from enum import Enum, auto

class EventType(Enum):
    """
    Enum class defining all event types in the system.
    Add new event types here as needed.
    """
    # Existing events
    TOOL_EXECUTION_STARTED = auto()
    TOOL_EXECUTION_COMPLETED = auto()
    TOOL_EXECUTION_FAILED = auto()
    WEIBO_POST_COMPLETED = auto() # Application-specific example
    TASK_COMPLETED = auto()
    TIMER_UPDATE = auto() # Example for timed events
    ASSISTANT_RESPONSE = auto() # For final assistant message

    # New events based on agent lifecycle and interactions
    AGENT_STARTED = auto() # Emitted when an agent's runtime starts
    AGENT_STOPPED = auto() # Emitted when an agent's runtime stops
    AGENT_STATUS_CHANGED = auto() # Emitted when an agent's status (idle, running, error, etc.) changes
    TOOL_APPROVAL_REQUESTED = auto() # Emitted when a tool execution requires external approval
