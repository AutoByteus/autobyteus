# file: autobyteus/autobyteus/agent_team/task_notification/task_notification_mode.py
"""
Defines the enum for controlling how task notifications are handled in an agent team.
"""
import os
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
    In this mode, the agent team framework automatically monitors the TaskPlan
    and sends notifications to agents when their assigned tasks become runnable.
    """

    def __str__(self) -> str:
        return self.value


ENV_TASK_NOTIFICATION_MODE = "AUTOBYTEUS_TASK_NOTIFICATION_MODE"
DEFAULT_TASK_NOTIFICATION_MODE = TaskNotificationMode.AGENT_MANUAL_NOTIFICATION
_VALID_TASK_NOTIFICATION_MODES = {mode.value: mode for mode in TaskNotificationMode}


def resolve_task_notification_mode() -> TaskNotificationMode:
    """
    Resolve task notification mode from environment.

    Env var: AUTOBYTEUS_TASK_NOTIFICATION_MODE
    """
    raw_value = os.getenv(ENV_TASK_NOTIFICATION_MODE)
    if not raw_value:
        return DEFAULT_TASK_NOTIFICATION_MODE
    normalized = raw_value.strip().lower()
    return _VALID_TASK_NOTIFICATION_MODES.get(normalized, DEFAULT_TASK_NOTIFICATION_MODE)
