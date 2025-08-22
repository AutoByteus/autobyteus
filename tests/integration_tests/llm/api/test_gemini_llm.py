import pytest
import asyncio
import os
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY"))

@pytest.fixture
def gemini_llm(set_gemini_env):
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY":
        pytest.skip("Gemini API key not set. Skipping GeminiLLM tests.")
    
    return GeminiLLM(model=LLMModel['gemini-2.5-flash'], llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_gemini_llm_response(gemini_llm):
    user_message = LLMUserMessage(content="Hello, Gemini LLM!")
    response = await gemini_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_gemini_llm_streaming(gemini_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    async for chunk in gemini_llm._stream_user_message_to_llm(user_message):
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
    assert len(gemini_llm.messages) == 3

    await gemini_llm.cleanup()

@pytest.mark.asyncio
async def test_gemini_send_user_message(gemini_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await gemini_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(gemini_llm.messages) == 3
    assert gemini_llm.messages[1].content == user_message_text
    assert gemini_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_gemini_stream_user_message(gemini_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in gemini_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    assert len(gemini_llm.messages) == 3
    assert gemini_llm.messages[1].content == user_message_text
    assert gemini_llm.messages[2].content == complete_response

    await gemini_llm.cleanup()
