import pytest
import asyncio
import os
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.models import LLMModel

@pytest.fixture
def set_claude_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

@pytest.fixture
def claude_llm(set_claude_env):
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        pytest.skip("Anthropic API key not set. Skipping ClaudeLLM tests.")
    system_message = "You are a helpful assistant."
    return ClaudeLLM(model_name=LLMModel.CLAUDE_3_5_SONNET_API, system_message=system_message)

@pytest.mark.asyncio
async def test_claude_llm_response(claude_llm):
    user_message = "Hello, Claude LLM!"
    response = await claude_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_claude_llm_streaming(claude_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    async for token in claude_llm._stream_user_message_to_llm(user_message):
        # Verify each token is a string
        assert isinstance(token, str)
        received_tokens.append(token)
        complete_response += token
        
        # Print tokens as they arrive for debugging
        print(f"Received token: {token}")
    
    # Verify we received tokens
    assert len(received_tokens) > 0
    
    # Verify the complete response
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(claude_llm.messages) == 2  # User message + Assistant message
    assert claude_llm.messages[0].content == user_message
    assert claude_llm.messages[1].content == complete_response

    # Print final response for manual verification
    print(f"\nComplete response: {complete_response}")
    
    # Cleanup
    await claude_llm.cleanup()