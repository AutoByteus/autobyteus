import pytest
import asyncio
import os
from autobyteus.llm.api.nvidia_llm import NvidiaLLM

@pytest.fixture
def set_nvidia_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "YOUR_NVIDIA_API_KEY")

@pytest.fixture
def nvidia_llm(set_nvidia_env):
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_api_key:
        pytest.skip("Nvidia API key not set. Skipping NvidiaLLM tests.")
    model_name = None  # Use default model
    system_message = "You are a helpful assistant."
    return NvidiaLLM(model_name=model_name, system_message=system_message)

@pytest.mark.asyncio
async def test_nvidia_llm_response(nvidia_llm):
    user_message = "Hello, Nvidia LLM!"
    response = await nvidia_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, str)
    assert len(response) > 0