import pytest
import asyncio
import os
from autobyteus.llm.api.mistral_llm import MistralLLM

@pytest.fixture
def set_mistral_env(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "")

@pytest.fixture
def mistral_llm(set_mistral_env):
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key:
        pytest.skip("Mistral API key not set. Skipping MistralLLM tests.")
    model_name = None  # Use default model
    return MistralLLM(model_name=model_name)

@pytest.mark.asyncio
async def test_mistral_llm_response(mistral_llm):
    user_message = "Hello, Mistral LLM!"
    response = await mistral_llm._send_user_message_to_llm(user_message)
    print(response)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_mistral_llm_streaming(mistral_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    async for token in mistral_llm._stream_user_message_to_llm(user_message):
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
    assert len(mistral_llm.messages) == 2  # User message + Assistant message
    assert mistral_llm.messages[0].content == user_message
    assert mistral_llm.messages[1].content == complete_response

    # Print final response for manual verification
    print(f"\nComplete response: {complete_response}")
    
    # Cleanup
    await mistral_llm.cleanup()