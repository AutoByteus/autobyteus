import pytest
import asyncio
import os
from autobyteus.llm.api.gemini_llm import GeminiLLM

@pytest.fixture
def set_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

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
    user_message = "Hello, Gemini LLM!"
    response = await gemini_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, str)
    assert len(response) > 0