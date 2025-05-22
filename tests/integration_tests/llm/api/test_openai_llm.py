import pytest
import asyncio
import os
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")  # Replace with a valid API key for testing

@pytest.fixture
def openai_llm(set_openai_env):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        pytest.skip("OpenAI API key not set. Skipping OpenAILLM tests.")
    return OpenAILLM(model=LLMModel.GPT_4o_API)

@pytest.mark.asyncio
async def test_openai_llm_response(openai_llm):
    user_message = "Hello, OpenAI LLM!"
    response = await openai_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_openai_llm_streaming(openai_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    async for token in openai_llm._stream_user_message_to_llm(user_message):
        # Verify each token is a string
        assert isinstance(token, ChunkResponse)
        if token.content:
            assert isinstance(token.content, str)
            received_tokens.append(token.content)
            complete_response += token.content
        
        if token.is_complete:
            if token.usage:
                assert isinstance(token.usage, TokenUsage)
    
    # Verify we received tokens
    assert len(received_tokens) > 0
    
    # Verify the complete response
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(openai_llm.messages) == 3  # System message + User message + Assistant message

    # Cleanup
    await openai_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(openai_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text?"
    user_message = LLMUserMessage(content=user_message_text)
    response = await openai_llm.send_user_message(user_message)
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify message history was updated correctly
    assert len(openai_llm.messages) == 3  # System message + User message + Assistant message
    assert openai_llm.messages[1].content[0]["text"] == user_message_text  # Content is now structured for multimodal support
    assert openai_llm.messages[2].content == response

@pytest.mark.asyncio
async def test_stream_user_message(openai_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for token in openai_llm.stream_user_message(user_message):
        # Verify each token is a string
        assert isinstance(token, str)
        received_tokens.append(token)
        complete_response += token
    
    # Verify we received tokens
    assert len(received_tokens) > 0
    
    # Verify the complete response
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(openai_llm.messages) == 3  # System message + User message + Assistant message
    assert openai_llm.messages[1].content[0]["text"] == user_message_text  # Content is now structured for multimodal support
    assert openai_llm.messages[2].content == complete_response

    # Cleanup
    await openai_llm.cleanup()
