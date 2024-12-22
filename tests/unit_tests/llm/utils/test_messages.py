from autobyteus.llm.utils.messages import MessageRole, Message
import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_mistral_messages(mocker):
    mock_user_msg = mocker.patch("mistralai.UserMessage")
    mock_assistant_msg = mocker.patch("mistralai.AssistantMessage")
    return mock_user_msg, mock_assistant_msg


def test_to_mistral_message_user_role(mock_mistral_messages):
    mock_user_msg, _ = mock_mistral_messages
    content = "Hello, Mistral LLM!"
    message = Message(MessageRole.USER, content)

    result = message.to_mistral_message()

    mock_user_msg.assert_called_once_with(content=content)
    assert result == mock_user_msg.return_value


def test_to_mistral_message_assistant_role(mock_mistral_messages):
    _, mock_assistant_msg = mock_mistral_messages
    content = "Here's the response"
    message = Message(MessageRole.ASSISTANT, content)

    result = message.to_mistral_message()

    mock_assistant_msg.assert_called_once_with(content=content)
    assert result == mock_assistant_msg.return_value


def test_to_mistral_message_system_role(mock_mistral_messages):
    mock_user_msg, mock_assistant_msg = mock_mistral_messages
    content = "System message"
    message = Message(MessageRole.SYSTEM, content)

    result = message.to_mistral_message()

    mock_user_msg.assert_not_called()
    mock_assistant_msg.assert_not_called()
    assert result is None


def test_to_mistral_message_with_image_content(mock_mistral_messages):
    mock_user_msg, _ = mock_mistral_messages
    content = [
        {"type": "text", "content": "Here's an image"},
        {"type": "image", "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="},
    ]
    message = Message(MessageRole.USER, content)

    result = message.to_mistral_message()

    print(result)

    mock_user_msg.assert_called_once_with(content=content)
    assert result == mock_user_msg.return_value


def test_message_to_dict():
    content = "Test content"
    message = Message(MessageRole.USER, content)

    result = message.to_dict()

    expected = {"role": "user", "content": content}
    assert result == expected


def test_to_mistral_message_with_chunks(mock_mistral_messages):
    mock_user_msg, _ = mock_mistral_messages
    content = [
        {"type": "text", "content": "Hello"},
        {"type": "image", "image_url": "data:image/jpeg;base64,abc"},
    ]
    message = Message(MessageRole.USER, content)

    result = message.to_mistral_message()

    expected_content = [{"text": "Hello"}, {"image_url": "data:image/jpeg;base64,abc"}]

    mock_user_msg.assert_called_once_with(content=expected_content)
    assert result == mock_user_msg.return_value
