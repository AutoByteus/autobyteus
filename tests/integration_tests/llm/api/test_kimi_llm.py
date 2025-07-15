import pytest
import asyncio
import os
from autobyteus.llm.api.kimi_llm import KimiLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig

@pytest.fixture
def set_kimi_env(monkeypatch):
    monkeypatch.setenv("KIMI_API_KEY", os.getenv("KIMI_API_KEY", "YOUR_KIMI_API_KEY"))

@pytest.fixture
def kimi_llm(set_kimi_env):
    kimi_api_key = os.getenv("KIMI_API_KEY")
    if not kimi_api_key or kimi_api_key == "YOUR_KIMI_API_KEY":
        pytest.skip("Kimi API key not set. Skipping KimiLLM tests.")
    return KimiLLM(model=LLMModel['kimi-latest'], llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_kimi_llm_response(kimi_llm):
    """Test a non-streaming response from the KimiLLM."""
    user_message = "Hello, Kimi LLM! Please respond with 'pong'."
    response = await kimi_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert "pong" in response.content.lower()
    assert response.usage is not None
    assert response.usage.total_tokens > 0

@pytest.mark.asyncio
async def test_kimi_llm_streaming(kimi_llm): 
    """Test that streaming returns tokens incrementally and builds a complete response."""
    user_message = "Please write a short two-sentence greeting."
    received_tokens = []
    complete_response = ""
    
    async for chunk in kimi_llm._stream_user_message_to_llm(user_message):
        assert isinstance(chunk, ChunkResponse)
        if chunk.content:
            assert isinstance(chunk.content, str)
            received_tokens.append(chunk.content)
            complete_response += chunk.content
        
        if chunk.is_complete:
            assert chunk.usage is not None
            assert isinstance(chunk.usage, TokenUsage)
            assert chunk.usage.total_tokens > 0
    
    assert len(received_tokens) > 1
    assert len(complete_response) > 10
    assert isinstance(complete_response, str)
    assert len(kimi_llm.messages) == 3  # System message + User message + Assistant message

    await kimi_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(kimi_llm):
    """Test the public API send_user_message for KimiLLM."""
    user_message_text = "Who developed the programming language Python?"
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await kimi_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert "guido van rossum" in response_obj.content.lower()

    # Verify message history was updated correctly
    assert len(kimi_llm.messages) == 3
    assert kimi_llm.messages[1].content[0]["text"] == user_message_text
    assert kimi_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_stream_user_message(kimi_llm):
    """Test the public API stream_user_message for KimiLLM."""
    user_message_text = "Please list three popular web frameworks for Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in kimi_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 1
    assert "django" in complete_response.lower()
    assert "flask" in complete_response.lower()
    
    # Verify message history was updated correctly
    assert len(kimi_llm.messages) == 3
    assert kimi_llm.messages[1].content[0]["text"] == user_message_text
    assert kimi_llm.messages[2].content == complete_response

    await kimi_llm.cleanup()
