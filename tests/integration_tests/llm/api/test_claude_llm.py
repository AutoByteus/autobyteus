import pytest
import asyncio
import os
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.models_bak import LLMModel

@pytest.fixture
def set_claude_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

@pytest.fixture
def claude_llm(set_claude_env):
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        pytest.skip("Anthropic API key not set. Skipping ClaudeLLM tests.")
    system_message = "You are a helpful assistant."
    return ClaudeLLM(model_name=LLMModel.CLAUDE_3_HAIKU_API, system_message=system_message)

@pytest.mark.asyncio
async def test_claude_llm_response(claude_llm):
    user_message = "Hello, Claude LLM!"
    response = await claude_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, str)
    assert len(response) > 0