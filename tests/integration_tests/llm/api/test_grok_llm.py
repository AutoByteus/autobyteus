import pytest
import asyncio
import os
from autobyteus.llm.api.grok_llm import GrokLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
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
        pytest.skip("Grok API key not set. Skipping GrokLLM tests.")
    return GrokLLM(model=LLMModel['grok-2-1212'], llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_grok_llm_response(grok_llm):
    user_message = LLMUserMessage(content="Hello, Grok LLM!")
    response = await grok_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_grok_llm_streaming(grok_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    async for chunk in grok_llm._stream_user_message_to_llm(user_message):
        assert isinstance(chunk, ChunkResponse)
        if chunk.content:
            assert isinstance(chunk.content, str)
            received_tokens.append(chunk.content)
            complete_response += chunk.content
        
        if chunk.is_complete:
            if chunk.usage:
                assert isinstance(chunk.usage, TokenUsage)
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    assert len(grok_llm.messages) == 3

    await grok_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(grok_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await grok_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(grok_llm.messages) == 3
    assert grok_llm.messages[1].content == user_message_text
    assert grok_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_stream_user_message(grok_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in grok_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    assert len(grok_llm.messages) == 3
    assert grok_llm.messages[1].content == user_message_text
    assert grok_llm.messages[2].content == complete_response

    await grok_llm.cleanup()
