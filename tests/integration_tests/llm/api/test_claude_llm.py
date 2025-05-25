import pytest
import asyncio
import os
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig # Added import

@pytest.fixture
def set_claude_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY"))  # Use actual env var or placeholder

@pytest.fixture
def claude_llm(set_claude_env):
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        pytest.skip("Anthropic API key not set. Skipping ClaudeLLM tests.")
    return ClaudeLLM(model=LLMModel.CLAUDE_3_5_SONNET_API, llm_config=LLMConfig()) # Use CLAUDE_3_5_SONNET_API as per LLMModel.py context

@pytest.mark.asyncio
async def test_claude_llm_response(claude_llm):
    user_message = "Hello, Claude LLM!"
    response = await claude_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_claude_llm_streaming(claude_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    async for chunk in claude_llm._stream_user_message_to_llm(user_message):
        assert isinstance(chunk, ChunkResponse)
        if chunk.content:
            assert isinstance(chunk.content, str)
            received_tokens.append(chunk.content)
            complete_response += chunk.content
        
        if chunk.is_complete:
            if chunk.usage:
                assert isinstance(chunk.usage, TokenUsage)
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    assert len(claude_llm.messages) == 3  # System message + User message + Assistant message

    await claude_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(claude_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text?"
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await claude_llm.send_user_message(user_message) # Changed variable name to avoid confusion
    
    assert isinstance(response_obj, CompleteResponse) # Assert it's the CompleteResponse object
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    # Verify message history was updated correctly
    assert len(claude_llm.messages) == 3  # System message + User message + Assistant message
    assert claude_llm.messages[1].content == user_message_text
    assert claude_llm.messages[2].content == response_obj.content # Access content attribute

@pytest.mark.asyncio
async def test_stream_user_message(claude_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in claude_llm.stream_user_message(user_message): # Iterate over ChunkResponse
        assert isinstance(chunk, ChunkResponse) # Expect ChunkResponse
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(claude_llm.messages) == 3  # System message + User message + Assistant message
    assert claude_llm.messages[1].content == user_message_text
    assert claude_llm.messages[2].content == complete_response

    await claude_llm.cleanup()
