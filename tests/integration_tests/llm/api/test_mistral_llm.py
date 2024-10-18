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