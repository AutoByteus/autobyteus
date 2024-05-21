# File path: tests/unit_tests/llm_integrations/openai_integration/test_openai_message_types.py

import pytest
from autobyteus.llm.openai.openai_message_types import OpenAIMessageRole, BaseMessage, SystemMessage, UserMessage, AssistantMessage, MessageList

def test_openai_message_role_contains_expected_roles():
    """Ensure the OpenAIMessageRole enum contains the expected roles."""
    expected_roles = {"SYSTEM", "USER", "ASSISTANT"}
    assert set(OpenAIMessageRole._member_names_) == expected_roles

@pytest.mark.parametrize("MessageClass, expected_role", [
    (SystemMessage, OpenAIMessageRole.SYSTEM),
    (UserMessage, OpenAIMessageRole.USER),
    (AssistantMessage, OpenAIMessageRole.ASSISTANT)
])
def test_derived_message_classes_initialization_and_to_dict(MessageClass, expected_role):
    """Test the initialization and to_dict method of the derived message classes."""
    message_content = "Test Content"
    message = MessageClass(message_content)
    assert message.content == message_content
    assert message.role == expected_role
    assert message.to_dict() == {"role": expected_role.value, "content": message_content}

def test_message_list_functionality():
    """Test the functionality of the MessageList class."""
    message_list = MessageList()
    
    user_message_content = "This is a user message."
    system_message_content = "This is a system message."
    assistant_message_content = "This is an assistant message."
    
    message_list.add_user_message(user_message_content)
    message_list.add_system_message(system_message_content)
    message_list.add_assistant_message(assistant_message_content)
    
    messages = message_list.get_messages()
    assert len(messages) == 3
    assert messages[0]['role'] == OpenAIMessageRole.SYSTEM.value
    assert messages[0]['content'] == system_message_content
    assert messages[1]['role'] == OpenAIMessageRole.USER.value
    assert messages[1]['content'] == user_message_content
    assert messages[2]['role'] == OpenAIMessageRole.ASSISTANT.value
    assert messages[2]['content'] == assistant_message_content

def test_message_list_default_system_message():
    """Ensure that the MessageList adds a default system message if none is provided."""
    message_list = MessageList()
    user_message_content = "This is a user message."
    message_list.add_user_message(user_message_content)
    
    messages = message_list.get_messages()
    assert len(messages) == 2
    assert messages[0]['role'] == OpenAIMessageRole.SYSTEM.value
    assert messages[0]['content'] == "You are a helpful assistant."
