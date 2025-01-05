
from enum import Enum


class AgentStatus(Enum):
    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    WAITING_FOR_RESPONSE = "waiting_for_response"
    IDLE = "idle"
    ENDED = "ended"
    ERROR = "error"
