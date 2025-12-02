import pytest
import os
from autobyteus.llm.api.grok_llm import GrokLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig


@pytest.fixture
def set_grok_env(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", os.getenv("GROK_API_KEY", "YOUR_GROK_API_KEY"))


@pytest.fixture
def grok_llm(set_grok_env):
    grok_api_key = os.getenv("GROK_API_KEY")
    if not grok_api_key or grok_api_key == "YOUR_GROK_API_KEY":
        pytest.skip("GROK_API_KEY not set. Skipping GrokLLM tests.")
    return GrokLLM(model=LLMModel["grok-4-1-fast-reasoning"])


@pytest.mark.asyncio
async def test_grok_llm_response(grok_llm):
    user_message = LLMUserMessage(content="Say hello in five words.")
    response = await grok_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert 0 < len(response.content.split()) <= 10


@pytest.mark.asyncio
async def test_grok_llm_streaming(grok_llm):
    user_message = LLMUserMessage(content="List three colors.")
    received_tokens = []
    complete_response = ""

    async for chunk in grok_llm._stream_user_message_to_llm(user_message):
        assert isinstance(chunk, ChunkResponse)
        if chunk.content:
            received_tokens.append(chunk.content)
            complete_response += chunk.content
        if chunk.is_complete and chunk.usage:
            assert isinstance(chunk.usage, TokenUsage)

    assert len(received_tokens) > 0
    assert len(complete_response) > 0

    await grok_llm.cleanup()
