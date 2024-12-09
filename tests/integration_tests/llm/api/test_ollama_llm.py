import pytest
import asyncio
import os
from autobyteus.llm.api.ollama_llm import OllamaLLM
from autobyteus.llm.models import LLMModel

@pytest.fixture
def ollama_llm():
    system_message = "You are a helpful assistant."
    return OllamaLLM(model_name=LLMModel.LLAMA_3_2_LOCAL, system_message=system_message)

@pytest.mark.asyncio
async def test_ollama_llm_response(ollama_llm):
    user_message = "Hello, Ollama LLM!"
    response = await ollama_llm._send_user_message_to_llm(user_message)
    print("🧐🧐🧐🧐 %s", response)
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_ollama_llm_streaming(ollama_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""

    async for token in ollama_llm._stream_user_message_to_llm(user_message):
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
    assert len(ollama_llm.messages) == 2  # User message + Assistant message
    assert ollama_llm.messages[0].content == user_message
    assert ollama_llm.messages[1].content == complete_response

    # Print final response for manual verification
    print(f"\nComplete response: {complete_response}")

    # Cleanup
    await ollama_llm.cleanup()