import pytest
import asyncio
import os
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_mistral_env(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "")  # Replace with a valid API key for testing

@pytest.fixture
def mistral_llm(set_mistral_env):
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key:
        pytest.skip("Mistral API key not set. Skipping MistralLLM tests.")
    return MistralLLM(model=LLMModel.MISTRAL_LARGE_API)

@pytest.mark.asyncio
async def test_mistral_llm_response(mistral_llm):
    user_message = "Hello, Mistral LLM!"
    response = await mistral_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_mistral_llm_streaming(mistral_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    async for token in mistral_llm._stream_user_message_to_llm(user_message):
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
    assert len(mistral_llm.messages) == 3  # System message + User message + Assistant message

    await mistral_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(mistral_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text?"
    user_message = LLMUserMessage(content=user_message_text)
    response = await mistral_llm.send_user_message(user_message)
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify message history was updated correctly
    assert len(mistral_llm.messages) == 3  # System message + User message + Assistant message
    assert mistral_llm.messages[1].content == user_message_text
    assert mistral_llm.messages[2].content == response

@pytest.mark.asyncio
async def test_stream_user_message(mistral_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for token in mistral_llm.stream_user_message(user_message):
        assert isinstance(token, str)
        received_tokens.append(token)
        complete_response += token
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(mistral_llm.messages) == 3  # System message + User message + Assistant message
    assert mistral_llm.messages[1].content == user_message_text
    assert mistral_llm.messages[2].content == complete_response

    await mistral_llm.cleanup()
