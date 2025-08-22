import pytest
import asyncio
import os
from autobyteus.llm.api.nvidia_llm import NvidiaLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_nvidia_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", os.getenv("NVIDIA_API_KEY", "YOUR_NVIDIA_API_KEY"))

@pytest.fixture
def nvidia_llm(set_nvidia_env):
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_api_key or nvidia_api_key == "YOUR_NVIDIA_API_KEY":
        pytest.skip("Nvidia API key not set. Skipping NvidiaLLM tests.")
    
    return NvidiaLLM(model=LLMModel.NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API, llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_nvidia_llm_response(nvidia_llm):
    user_message = LLMUserMessage(content="Hello, Nvidia LLM!")
    response = await nvidia_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_nvidia_llm_streaming(nvidia_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    async for chunk in nvidia_llm._stream_user_message_to_llm(user_message):
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
    assert len(nvidia_llm.messages) == 3

    await nvidia_llm.cleanup()

@pytest.mark.asyncio
async def test_nvidia_send_user_message(nvidia_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await nvidia_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(nvidia_llm.messages) == 3
    assert nvidia_llm.messages[1].content == user_message_text
    assert nvidia_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_nvidia_stream_user_message(nvidia_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in nvidia_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    assert len(nvidia_llm.messages) == 3
    assert nvidia_llm.messages[1].content == user_message_text
    assert nvidia_llm.messages[2].content == complete_response

    await nvidia_llm.cleanup()
