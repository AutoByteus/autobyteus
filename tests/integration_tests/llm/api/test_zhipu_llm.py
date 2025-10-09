import os
import pytest

from autobyteus.llm.api.zhipu_llm import ZhipuLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage


@pytest.fixture
def set_zhipu_env(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", os.getenv("ZHIPU_API_KEY", "YOUR_ZHIPU_API_KEY"))


@pytest.fixture
def zhipu_llm(set_zhipu_env):
    zhipu_api_key = os.getenv("ZHIPU_API_KEY")
    if not zhipu_api_key or zhipu_api_key == "YOUR_ZHIPU_API_KEY":
        pytest.skip("Zhipu API key not set. Skipping ZhipuLLM tests.")
    return ZhipuLLM(model=LLMModel["glm-4.6"], llm_config=LLMConfig())


@pytest.mark.asyncio
async def test_zhipu_llm_response(zhipu_llm):
    """Test a non-streaming response from the ZhipuLLM."""
    user_message = LLMUserMessage(content="Hello, Zhipu LLM! Please respond with a short greeting.")
    response = await zhipu_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_zhipu_llm_streaming(zhipu_llm):
    """Test that streaming returns tokens incrementally and builds a complete response."""
    user_message = LLMUserMessage(content="Please write a short two-sentence greeting.")
    received_tokens = []
    complete_response = ""

    async for chunk in zhipu_llm._stream_user_message_to_llm(user_message):
        assert isinstance(chunk, ChunkResponse)
        if chunk.content:
            assert isinstance(chunk.content, str)
            received_tokens.append(chunk.content)
            complete_response += chunk.content

        if chunk.is_complete and chunk.usage:
            assert isinstance(chunk.usage, TokenUsage)

    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    assert len(zhipu_llm.messages) == 3

    await zhipu_llm.cleanup()


@pytest.mark.asyncio
async def test_send_user_message(zhipu_llm):
    """Test the public API send_user_message for ZhipuLLM."""
    user_message_text = "Can you summarize the origin of the Python programming language?"
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await zhipu_llm.send_user_message(user_message)

    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(zhipu_llm.messages) == 3
    assert zhipu_llm.messages[1].content == user_message_text
    assert zhipu_llm.messages[2].content == response_obj.content


@pytest.mark.asyncio
async def test_stream_user_message(zhipu_llm):
    """Test the public API stream_user_message for ZhipuLLM."""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""

    async for chunk in zhipu_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content

    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)

    assert len(zhipu_llm.messages) == 3
    assert zhipu_llm.messages[1].content == user_message_text
    assert zhipu_llm.messages[2].content == complete_response

    await zhipu_llm.cleanup()
