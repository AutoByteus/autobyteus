import pytest
import asyncio
import os
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig

@pytest.fixture
def set_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "")) # Use actual env var or placeholder

@pytest.fixture
def openai_llm(set_openai_env):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        pytest.skip("OpenAI API key not set. Skipping OpenAILLM tests.")
    return OpenAILLM(model=LLMModel['gpt-4o'], llm_config=LLMConfig())

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
    
    async for chunk in openai_llm._stream_user_message_to_llm(user_message):
        assert isinstance(chunk, ChunkResponse) # Verify each chunk is a ChunkResponse
        if chunk.content:
            assert isinstance(chunk.content, str)
            received_tokens.append(chunk.content)
            complete_response += chunk.content
        
        if chunk.is_complete:
            if chunk.usage:
                assert isinstance(chunk.usage, TokenUsage)
    
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
    response_obj = await openai_llm.send_user_message(user_message) # Changed variable name
    
    assert isinstance(response_obj, CompleteResponse) # Assert it's the CompleteResponse object
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    # Verify message history was updated correctly
    assert len(openai_llm.messages) == 3  # System message + User message + Assistant message
    assert isinstance(openai_llm.messages[1].content, list)
    assert openai_llm.messages[1].content[0]["text"] == user_message_text
    assert openai_llm.messages[2].content == response_obj.content # Access content attribute

@pytest.mark.asyncio
async def test_stream_user_message(openai_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in openai_llm.stream_user_message(user_message): # Iterate over ChunkResponse
        assert isinstance(chunk, ChunkResponse) # Verify each chunk is a ChunkResponse
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    # Verify we received tokens
    assert len(received_tokens) > 0
    
    # Verify the complete response
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(openai_llm.messages) == 3  # System message + User message + Assistant message
    assert isinstance(openai_llm.messages[1].content, list)
    assert openai_llm.messages[1].content[0]["text"] == user_message_text
    assert openai_llm.messages[2].content == complete_response

    # Cleanup
    await openai_llm.cleanup()
