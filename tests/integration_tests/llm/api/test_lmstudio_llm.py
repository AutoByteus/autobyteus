import pytest
import asyncio
import os
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from openai import APIConnectionError

# Path to the test asset
TEST_IMAGE_PATH = "autobyteus/tests/assets/sample_image.png"
USER_PROVIDED_IMAGE_URL = "https://127.0.0.1:51739/media/images/b132adbb-80e4-4faf-bd36-44d965d2e095.jpg"

@pytest.fixture
def set_lmstudio_env(monkeypatch):
    """Set the dummy API key required by the OpenAI client."""
    monkeypatch.setenv("LMSTUDIO_API_KEY", os.getenv("LMSTUDIO_API_KEY", "lm-studio"))

@pytest.fixture
def lmstudio_llm(set_lmstudio_env):
    """
    Fixture to provide an LMStudioLLM instance for a vision model.
    Skips tests if a suitable model is not found.
    """
    # Re-initialize to ensure discovery of local models
    LLMFactory.reinitialize()
    
    # CORRECT: List models by the LMStudio RUNTIME
    lmstudio_models = LLMFactory.list_models_by_runtime(LLMRuntime.LMSTUDIO)
    
    if not lmstudio_models:
        pytest.skip(
            "No LM Studio models found. Skipping tests. "
            "Ensure LM Studio is running with the server started and at least one model loaded."
        )
    
    # List of known keywords for multimodal models, including the user-specified one
    vision_keywords = ["gemma-3n-e4b", "llava", "gemma"]

    # Find the first available model that matches one of the vision keywords
    vision_model = next((m for m in lmstudio_models if any(known in m.model_identifier for known in vision_keywords)), None)

    if not vision_model:
        pytest.skip(f"No known vision model (e.g., {', '.join(vision_keywords)}) found in LM Studio. Skipping multimodal tests.")
    
    model_identifier = vision_model.model_identifier
    
    try:
        return LLMFactory.create_llm(model_identifier=model_identifier)
    except Exception as e:
        pytest.skip(f"Failed to create LM Studio LLM for model '{model_identifier}'. Error: {e}")

@pytest.mark.asyncio
async def test_lmstudio_llm_response(lmstudio_llm):
    """Test a non-streaming response from an LM Studio model."""
    user_message = LLMUserMessage(content="Hello! Please respond with 'pong'.")
    
    try:
        response = await lmstudio_llm.send_user_message(user_message)
        
        assert isinstance(response, CompleteResponse)
        assert isinstance(response.content, str)
        assert "pong" in response.content.lower()
        
        assert len(lmstudio_llm.messages) == 3
        assert lmstudio_llm.messages[1].content == user_message.content
        assert lmstudio_llm.messages[2].content == response.content

    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server. Skipping test.")
    finally:
        await lmstudio_llm.cleanup()

@pytest.mark.asyncio
@pytest.mark.parametrize("image_source", [
    TEST_IMAGE_PATH,
    pytest.param(USER_PROVIDED_IMAGE_URL, marks=pytest.mark.xfail(
        reason="This test requires a specific local server running at the specified URL with a trusted SSL cert."
    ))
])
async def test_lmstudio_llm_multimodal_response(lmstudio_llm, image_source):
    """Test a multimodal (text + image) response from an LM Studio model."""
    if image_source == TEST_IMAGE_PATH and not os.path.exists(TEST_IMAGE_PATH):
        pytest.skip(f"Test image not found at {TEST_IMAGE_PATH}")
        
    user_message = LLMUserMessage(
        content="What is in this image? Describe it in one word.",
        image_urls=[image_source]
    )
    
    try:
        response = await lmstudio_llm.send_user_message(user_message)
        assert isinstance(response, CompleteResponse)
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server. Skipping test.")
    except Exception as e:
        pytest.fail(f"LM Studio multimodal test failed unexpectedly. Error: {e}")
    finally:
        await lmstudio_llm.cleanup()

@pytest.mark.asyncio
async def test_lmstudio_llm_streaming(lmstudio_llm): 
    """Test a streaming response from an LM Studio model."""
    user_message = LLMUserMessage(content="Write a short, two-sentence story about a robot.")
    complete_response = ""
    
    try:
        async for chunk in lmstudio_llm.stream_user_message(user_message):
            assert isinstance(chunk, ChunkResponse)
            if chunk.content:
                assert isinstance(chunk.content, str)
                complete_response += chunk.content
            
            if chunk.is_complete and chunk.usage:
                assert isinstance(chunk.usage, TokenUsage)
    
        assert len(complete_response) > 10
        
        assert len(lmstudio_llm.messages) == 3
        assert lmstudio_llm.messages[1].content == user_message.content
        assert lmstudio_llm.messages[2].content == complete_response

    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server. Skipping test.")
    finally:
        await lmstudio_llm.cleanup()
