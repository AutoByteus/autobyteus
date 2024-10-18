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