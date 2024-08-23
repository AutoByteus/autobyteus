from autobyteus.agent.message.message_types import MessageType

class Message:
    def __init__(self, recipient_role_name: str, recipient_agent_id: str, content: str, 
                 message_type: MessageType, sender_agent_id: str):
        self.recipient_role_name = recipient_role_name
        self.recipient_agent_id = recipient_agent_id
        self.content = content
        self.message_type = message_type
        self.sender_agent_id = sender_agent_id

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        return (self.recipient_role_name == other.recipient_role_name and
                self.recipient_agent_id == other.recipient_agent_id and
                self.content == other.content and
                self.message_type == other.message_type and
                self.sender_agent_id == other.sender_agent_id)

    def __repr__(self):
        return (f"Message(recipient_role_name='{self.recipient_role_name}', "
                f"recipient_agent_id='{self.recipient_agent_id}', "
                f"content='{self.content}', "
                f"message_type=<{self.message_type.__class__.__name__}.{self.message_type.name}: '{self.message_type.value}'>, "
                f"sender_agent_id='{self.sender_agent_id}')")

    @classmethod
    def create_with_dynamic_message_type(cls, recipient_role_name: str, recipient_agent_id: str,
                                         content: str, message_type: str, sender_agent_id: str):
        if not message_type:
            raise ValueError("message_type cannot be empty")
        
        try:
            msg_type = MessageType(message_type.lower())
        except ValueError:
            msg_type = MessageType.add_type(message_type.upper(), message_type.lower())
            if msg_type is None:
                raise ValueError(f"Failed to create or find MessageType: {message_type}")
        
        return cls(recipient_role_name, recipient_agent_id, content, msg_type, sender_agent_id)