import pytest
import asyncio
import os
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.llm_config import LLMConfig

# Path to the test asset
TEST_IMAGE_PATH = "autobyteus/tests/assets/sample_image.png"

@pytest.fixture
def set_mistral_env(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", os.getenv("MISTRAL_API_KEY", "YOUR_MISTRAL_API_KEY"))

@pytest.fixture
def mistral_llm(set_mistral_env):
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key or mistral_api_key == "YOUR_MISTRAL_API_KEY":
        pytest.skip("Mistral API key not set. Skipping MistralLLM tests.")
    return MistralLLM(model=LLMModel['devstral-2'], llm_config=LLMConfig())

@pytest.mark.asyncio
async def test_mistral_llm_response(mistral_llm):
    user_message = LLMUserMessage(content="Hello, Mistral LLM!")
    response = await mistral_llm._send_user_message_to_llm(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_mistral_llm_multimodal_response(mistral_llm):
    if not os.path.exists(TEST_IMAGE_PATH):
        pytest.skip(f"Test image not found at {TEST_IMAGE_PATH}")
        
    user_message = LLMUserMessage(
        content="Describe this image in one word.",
        image_urls=[TEST_IMAGE_PATH]
    )
    response = await mistral_llm.send_user_message(user_message)
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_mistral_llm_streaming(mistral_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    async for chunk in mistral_llm._stream_user_message_to_llm(user_message):
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
    assert len(mistral_llm.messages) == 3

    await mistral_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(mistral_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    response_obj = await mistral_llm.send_user_message(user_message)
    
    assert isinstance(response_obj, CompleteResponse)
    assert isinstance(response_obj.content, str)
    assert len(response_obj.content) > 0

    assert len(mistral_llm.messages) == 3
    assert mistral_llm.messages[1].content == user_message_text
    assert mistral_llm.messages[2].content == response_obj.content

@pytest.mark.asyncio
async def test_stream_user_message(mistral_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    async for chunk in mistral_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        assert isinstance(chunk.content, str)
        received_tokens.append(chunk.content)
        complete_response += chunk.content
    
    assert len(received_tokens) > 0
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    assert len(mistral_llm.messages) == 3
    assert mistral_llm.messages[1].content == user_message_text
    assert mistral_llm.messages[2].content == complete_response

    await mistral_llm.cleanup()
