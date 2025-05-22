import pytest
import asyncio
import os
from autobyteus.llm.api.deepseek_llm import DeepSeekLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_deepseek_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")  # Replace with a valid API key for testing

@pytest.fixture
def deepseek_llm(set_deepseek_env):
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        pytest.skip("DeepSeek API key not set. Skipping DeepSeekLLM tests.")
    return DeepSeekLLM(model=LLMModel.DEEPSEEK_CHAT_API)

@pytest.mark.asyncio
async def test_deepseek_llm_response(deepseek_llm):
    user_message = "Hello, DeepSeek LLM!"
    response = await deepseek_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_deepseek_llm_streaming(deepseek_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    async for token in deepseek_llm._stream_user_message_to_llm(user_message):
        assert isinstance(token, ChunkResponse)
        if token.content:
            assert isinstance(token.content, str)
            received_tokens.append(token.content)
            complete_response += token.content
        
        if token.is_complete:
            if token.usage:
                assert isinstance(token.usage, TokenUsage)
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    assert len(deepseek_llm.messages) == 3  # System message + User message + Assistant message

    await deepseek_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(deepseek_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text?"
    user_message = LLMUserMessage(content=user_message_text)
    response = await deepseek_llm.send_user_message(user_message)
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify message history was updated correctly
    assert len(deepseek_llm.messages) == 3  # System message + User message + Assistant message
    # DeepSeek uses structured content format for multimodal support
    assert deepseek_llm.messages[1].content[0]["text"] == user_message_text
    assert deepseek_llm.messages[2].content == response

@pytest.mark.asyncio
async def test_stream_user_message(deepseek_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for token in deepseek_llm.stream_user_message(user_message):
        assert isinstance(token, str)
        received_tokens.append(token)
        complete_response += token
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(deepseek_llm.messages) == 3  # System message + User message + Assistant message
    # DeepSeek uses structured content format for multimodal support
    assert deepseek_llm.messages[1].content[0]["text"] == user_message_text
    assert deepseek_llm.messages[2].content == complete_response

    await deepseek_llm.cleanup()
