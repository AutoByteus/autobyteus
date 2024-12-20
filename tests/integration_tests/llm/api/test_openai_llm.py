import pytest
import asyncio
import os
from autobyteus.llm.api.openai_llm import OpenAILLM

@pytest.fixture
def set_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

@pytest.fixture
def openai_llm(set_openai_env):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        pytest.skip("OpenAI API key not set. Skipping OpenAILLM tests.")
    model_name = None  # Use default model
    system_message = "You are a helpful assistant."
    return OpenAILLM(model_name=model_name, system_message=system_message)

@pytest.mark.asyncio
async def test_openai_llm_response(openai_llm):
    user_message = "Hello, OpenAI LLM!"
    response = await openai_llm._send_user_message_to_llm(user_message)
    print(user_message)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_openai_llm_streaming(openai_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    async for token in openai_llm._stream_user_message_to_llm(user_message):
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
    assert len(openai_llm.messages) == 3  # System message + User message + Assistant message
    assert openai_llm.messages[-2].content == user_message
    assert openai_llm.messages[-1].content == complete_response

    # Print final response for manual verification
    print(f"\nComplete response: {complete_response}")
    
    # Cleanup
    await openai_llm.cleanup()