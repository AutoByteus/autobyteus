import pytest
import asyncio
import os
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig

# Path to the test asset
TEST_IMAGE_PATH = "autobyteus/tests/assets/sample_image.png"

@pytest.fixture
def set_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))

@pytest.fixture
def openai_llm(set_openai_env):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key or openai_api_key == "YOUR_OPENAI_API_KEY":
        pytest.skip("OpenAI API key not set. Skipping OpenAILLM tests.")
    return OpenAILLM(model=LLMModel['gpt-5.1'])

@pytest.mark.asyncio
async def test_openai_llm_response(openai_llm):
    user_message = LLMUserMessage(content="Hello, OpenAI LLM!")
    response = await openai_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_openai_llm_multimodal_response(openai_llm):
    if not os.path.exists(TEST_IMAGE_PATH):
        pytest.skip(f"Test image not found at {TEST_IMAGE_PATH}")
        
    user_message = LLMUserMessage(
        content="What is in this image? Respond with a single word.",
        image_urls=[TEST_IMAGE_PATH]
    )
    response = await openai_llm.send_user_message(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    # A 1x1 transparent pixel could be described as "nothing", "transparent", "pixel", etc.
    # We just check for a plausible text response.
    assert len(response.content.split()) < 5 # Expect a short answer

@pytest.mark.asyncio
async def test_openai_llm_streaming(openai_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    async for chunk in openai_llm._stream_user_message_to_llm(user_message):
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
    assert len(openai_llm.messages) == 3

    await openai_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(openai_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await openai_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(openai_llm.messages) == 3
    assert openai_llm.messages[1].content == user_message_text
    assert openai_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_stream_user_message(openai_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in openai_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    assert len(openai_llm.messages) == 3
    assert openai_llm.messages[1].content == user_message_text
    assert openai_llm.messages[2].content == complete_response

    await openai_llm.cleanup()
