from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Dict


class ToolInteractionStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ToolInteraction:
    tool_call_id: str
    turn_id: Optional[str]
    tool_name: Optional[str]
    arguments: Optional[Dict[str, Any]]
    result: Optional[Any]
    error: Optional[str]
    status: ToolInteractionStatus
