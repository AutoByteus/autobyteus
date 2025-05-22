import pytest
import asyncio
import os
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_claude_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # Replace with a valid API key for testing

@pytest.fixture
def claude_llm(set_claude_env):
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        pytest.skip("Anthropic API key not set. Skipping ClaudeLLM tests.")
    return ClaudeLLM(model=LLMModel.CLAUDE_3_7_SONNET_API)

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
    
    async for token in claude_llm._stream_user_message_to_llm(user_message):
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
    assert len(claude_llm.messages) == 3  # System message + User message + Assistant message

    await claude_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(claude_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text?"
    user_message = LLMUserMessage(content=user_message_text)
    response = await claude_llm.send_user_message(user_message)
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify message history was updated correctly
    assert len(claude_llm.messages) == 3  # System message + User message + Assistant message
    assert claude_llm.messages[1].content == user_message_text
    assert claude_llm.messages[2].content == response

@pytest.mark.asyncio
async def test_stream_user_message(claude_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for token in claude_llm.stream_user_message(user_message):
        assert isinstance(token, str)
        received_tokens.append(token)
        complete_response += token
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(claude_llm.messages) == 3  # System message + User message + Assistant message
    assert claude_llm.messages[1].content == user_message_text
    assert claude_llm.messages[2].content == complete_response

    await claude_llm.cleanup()
