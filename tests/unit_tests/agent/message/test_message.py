import pytest
from autobyteus.agent.message.message import Message
from autobyteus.agent.message.message_types import MessageType

def test_message_initialization():
    message = Message("TestRole", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001")
    assert message.recipient_role_name == "TestRole"
    assert message.recipient_agent_id == "TestAgent-001"
    assert message.content == "Test content"
    assert message.message_type == MessageType.TASK_ASSIGNMENT
    assert message.sender_agent_id == "SenderAgent-001"

def test_message_attributes():
    message = Message("TestRole", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001")
    assert hasattr(message, 'recipient_role_name')
    assert hasattr(message, 'recipient_agent_id')
    assert hasattr(message, 'content')
    assert hasattr(message, 'message_type')
    assert hasattr(message, 'sender_agent_id')

def test_create_with_dynamic_type_existing_type():
    message = Message.create_with_dynamic_type("TestRole", "TestAgent-001", "Test content", "task_assignment", "SenderAgent-001")
    assert message.message_type == MessageType.TASK_ASSIGNMENT

def test_create_with_dynamic_type_new_type():
    message = Message.create_with_dynamic_type("TestRole", "TestAgent-001", "Test content", "new_type", "SenderAgent-001")
    assert message.message_type.value == "new_type"
    assert MessageType.NEW_TYPE.value == "new_type"

def test_create_with_dynamic_type_invalid_type():
    with pytest.raises(ValueError):
        Message.create_with_dynamic_type("TestRole", "TestAgent-001", "Test content", "", "SenderAgent-001")

def test_message_equality():
    message1 = Message("TestRole", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001")
    message2 = Message("TestRole", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001")
    message3 = Message("DifferentRole", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001")
    
    assert message1 == message2
    assert message1 != message3

def test_message_representation():
    message = Message("TestRole", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001")
    expected_repr = "Message(recipient_role_name='TestRole', recipient_agent_id='TestAgent-001', content='Test content', message_type=<MessageType.TASK_ASSIGNMENT: 'task_assignment'>, sender_agent_id='SenderAgent-001')"
    assert repr(message) == expected_repr


@pytest.mark.parametrize("role_name, agent_id, content, msg_type, sender_id", [
    ("", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001"),
    ("TestRole", "", "Test content", MessageType.TASK_ASSIGNMENT, "SenderAgent-001"),
    ("TestRole", "TestAgent-001", "", MessageType.TASK_ASSIGNMENT, "SenderAgent-001"),
    ("TestRole", "TestAgent-001", "Test content", MessageType.TASK_ASSIGNMENT, ""),
])
def test_message_initialization_with_empty_strings(role_name, agent_id, content, msg_type, sender_id):
    message = Message(role_name, agent_id, content, msg_type, sender_id)
    assert message.recipient_role_name == role_name
    assert message.recipient_agent_id == agent_id
    assert message.content == content
    assert message.message_type == msg_type
    assert message.sender_agent_id == sender_id