from enum import Enum

class MessageType(Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    TASK_COMPLETED = "task_completed"
    CLARIFICATION = "clarification"
    ERROR = "error"

class Message:
    def __init__(self, recipient_role_name: str, recipient_agent_id: str, content: str, message_type: MessageType, sender_agent_id: str):
        self.recipient_role_name = recipient_role_name
        self.recipient_agent_id = recipient_agent_id
        self.content = content
        self.message_type = message_type
        self.sender_agent_id = sender_agent_id