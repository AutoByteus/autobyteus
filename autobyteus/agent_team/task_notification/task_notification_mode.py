# file: autobyteus/autobyteus/agent_team/task_notification/task_notification_mode.py
"""
Defines the enum for controlling how task notifications are handled in an agent team.
"""
from enum import Enum

class TaskNotificationMode(str, Enum):
    """
    Enumerates the modes for handling task notifications within an agent team.
    """
    AGENT_MANUAL_NOTIFICATION = "agent_manual_notification"
    """
    In this mode, an agent (typically the coordinator) is responsible for
    manually sending notifications to other agents to start their tasks.
    """
    
    SYSTEM_EVENT_DRIVEN = "system_event_driven"
    """
    In this mode, the agent team framework automatically monitors the TaskBoard
    and sends notifications to agents when their assigned tasks become runnable.
    """

    def __str__(self) -> str:
        return self.value
