# file: autobyteus/autobyteus/agent/sender_type.py
from enum import Enum
from typing import Set

class SenderType(str, Enum):
    """
    Categorizes the origin of a message or event within the system.
    """
    USER = "user"        # A message originating from an external human user.
    AGENT = "agent"      # A message from another agent within the same team or a different team.
    SYSTEM = "system"    # An automated message from an internal system component.
    TOOL = "tool"        # A message generated as the result of a tool execution.


# --- System Sender Identification ---
TASK_NOTIFIER_SENDER_ID = "system.task_notifier"
