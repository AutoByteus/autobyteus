import pytest
import asyncio
import os
from autobyteus.llm.api.bedrock_llm import BedrockLLM
from autobyteus.llm.models import LLMModel 
from autobyteus.llm.utils.llm_config import LLMConfig 
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse 
from autobyteus.llm.utils.token_usage import TokenUsage 
from autobyteus.llm.user_message import LLMUserMessage 

@pytest.fixture
def set_bedrock_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", "YOUR_AWS_ACCESS_KEY_ID")) 
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "YOUR_AWS_SECRET_ACCESS_KEY")) 
    monkeypatch.setenv("AWS_REGION", os.getenv("AWS_REGION", "us-east-1"))

@pytest.fixture
def bedrock_llm(set_bedrock_env):
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not aws_access_key or not aws_secret_key or aws_access_key == "YOUR_AWS_ACCESS_KEY_ID":
        pytest.skip("AWS credentials not set. Skipping BedrockLLM tests.")
    
    return BedrockLLM(model=LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API, llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_bedrock_llm_response(bedrock_llm):
    user_message = LLMUserMessage(content="Hello, Bedrock LLM!")
    response = await bedrock_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse) 
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_bedrock_llm_streaming(bedrock_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    async for chunk in bedrock_llm._stream_user_message_to_llm(user_message):
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
    assert len(bedrock_llm.messages) == 3  # System message + User message + Assistant message

    await bedrock_llm.cleanup()

@pytest.mark.asyncio
async def test_bedrock_send_user_message(bedrock_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await bedrock_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(bedrock_llm.messages) == 3
    assert bedrock_llm.messages[1].content == user_message_text
    assert bedrock_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_bedrock_stream_user_message(bedrock_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in bedrock_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    assert len(bedrock_llm.messages) == 3
    assert bedrock_llm.messages[1].content == user_message_text
    assert bedrock_llm.messages[2].content == complete_response

    await bedrock_llm.cleanup()
