from autobyteus.agent.message.inter_agent_message_type import InterAgentMessageType 

class InterAgentMessage:
    def __init__(self, recipient_role_name: str, recipient_agent_id: str, content: str, 
                 message_type: InterAgentMessageType, sender_agent_id: str): # Updated type hint for message_type
        self.recipient_role_name = recipient_role_name
        self.recipient_agent_id = recipient_agent_id
        self.content = content
        self.message_type: InterAgentMessageType = message_type # Updated type hint for attribute
        self.sender_agent_id = sender_agent_id

    def __eq__(self, other):
        if not isinstance(other, InterAgentMessage): # Updated class check
            return False
        return (self.recipient_role_name == other.recipient_role_name and
                self.recipient_agent_id == other.recipient_agent_id and
                self.content == other.content and
                self.message_type == other.message_type and
                self.sender_agent_id == other.sender_agent_id)

    def __repr__(self):
        return (f"InterAgentMessage(recipient_role_name='{self.recipient_role_name}', " # Updated class name
                f"recipient_agent_id='{self.recipient_agent_id}', "
                f"content='{self.content}', "
                f"message_type=<{self.message_type.__class__.__name__}.{self.message_type.name}: '{self.message_type.value}'>, " # message_type class name will be InterAgentMessageType
                f"sender_agent_id='{self.sender_agent_id}')")

    @classmethod
    def create_with_dynamic_message_type(cls, recipient_role_name: str, recipient_agent_id: str,
                                         content: str, message_type: str, sender_agent_id: str) -> 'InterAgentMessage': # Updated return type hint
        if not message_type:
            raise ValueError("message_type cannot be empty")
        
        try:
            msg_type = InterAgentMessageType(message_type.lower()) # Use renamed InterAgentMessageType
        except ValueError:
            msg_type = InterAgentMessageType.add_type(message_type.upper(), message_type.lower()) # Use renamed InterAgentMessageType
            if msg_type is None:
                raise ValueError(f"Failed to create or find InterAgentMessageType: {message_type}") # Updated message
        
        return cls(recipient_role_name, recipient_agent_id, content, msg_type, sender_agent_id)
