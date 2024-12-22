import pytest
import asyncio
import os
from autobyteus.llm.api.gemini_llm import GeminiLLM


@pytest.fixture
def set_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")


@pytest.fixture
def gemini_llm(set_gemini_env):
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        pytest.skip("Gemini API key not set. Skipping GeminiLLM tests.")
    model_name = None  # Use default model
    system_message = "You are a helpful assistant."
    return GeminiLLM(model_name=model_name, system_message=system_message)


@pytest.mark.asyncio
async def test_gemini_llm_response(gemini_llm):
    user_message = "Hello, Gemini LLM! who is elon?"
    response = await gemini_llm._send_user_message_to_llm(user_message)

    ## For debugging
    print(response)

    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_gemini_llm_streaming(gemini_llm):
    """Test streaming functionality of GeminiLLM"""

    user_message = "write a finocai code please in python"
    received_tokens = []
    complete_response = ""

    async for token in gemini_llm._stream_user_message_to_llm(user_message):
        # Verify each token is a string
        assert isinstance(token, str)
        received_tokens.append(token)
        complete_response += token

        # Print tokens for debugging
        print(f"Received token: {token}")

    # Verify we received tokens
    assert len(received_tokens) > 0

    # Verify complete response
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)

    # Verify message history updated correctly
    assert len(gemini_llm.messages) == 3  # System + User + Assistant

    print(f"\nComplete response: {complete_response}")

    # Cleanup
    await gemini_llm.cleanup()
