
# File: autobyteus/events/event_types.py

from enum import Enum, auto

class EventType(Enum):
    """
    Enum class defining all event types in the system.
    Add new event types here as needed.
    """
    TOOL_EXECUTION_STARTED = auto()
    TOOL_EXECUTION_COMPLETED = auto()
    TOOL_EXECUTION_FAILED = auto()
    WEIBO_POST_COMPLETED = auto()
    TASK_COMPLETED = auto()  # New event type for task completion
    TIMER_UPDATE = auto()
    ASSISTANT_RESPONSE = auto()
