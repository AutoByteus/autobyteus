import pytest
import asyncio
import os
from autobyteus.llm.api.qwen_llm import QwenLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig

@pytest.fixture
def set_qwen_env(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY", "YOUR_DASHSCOPE_API_KEY"))

@pytest.fixture
def qwen_llm(set_qwen_env):
    qwen_api_key = os.getenv("DASHSCOPE_API_KEY")
    if not qwen_api_key or qwen_api_key == "YOUR_DASHSCOPE_API_KEY":
        pytest.skip("DashScope API key not set. Skipping QwenLLM tests.")
    return QwenLLM(model=LLMModel['qwen3-max'], llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_qwen_llm_response(qwen_llm):
    user_message = LLMUserMessage(content="Hello, Qwen LLM!")
    response = await qwen_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_qwen_llm_streaming(qwen_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    async for chunk in qwen_llm._stream_user_message_to_llm(user_message):
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
    assert len(qwen_llm.messages) == 3

    await qwen_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(qwen_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await qwen_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(qwen_llm.messages) == 3
    assert qwen_llm.messages[1].content == user_message_text
    assert qwen_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_stream_user_message(qwen_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in qwen_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    assert len(qwen_llm.messages) == 3
    assert qwen_llm.messages[1].content == user_message_text
    assert qwen_llm.messages[2].content == complete_response

    await qwen_llm.cleanup()
