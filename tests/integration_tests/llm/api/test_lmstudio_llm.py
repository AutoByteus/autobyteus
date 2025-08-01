import pytest
import asyncio
import os
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from openai import APIConnectionError

@pytest.fixture
def set_lmstudio_env(monkeypatch):
    """Set the dummy API key required by the OpenAI client."""
    monkeypatch.setenv("LMSTUDIO_API_KEY", os.getenv("LMSTUDIO_API_KEY", "lm-studio"))

@pytest.fixture
def lmstudio_llm(set_lmstudio_env):
    """
    Fixture to provide an LMStudioLLM instance.
    Skips tests if no LM Studio models are discovered.
    """
    # Re-initialize to ensure discovery of local models
    LLMFactory.reinitialize()
    
    # Get the list of discovered models for the LMSTUDIO provider
    lmstudio_models = LLMFactory.get_models_by_provider(LLMProvider.LMSTUDIO)
    
    if not lmstudio_models:
        pytest.skip(
            "No LM Studio models found. Skipping tests. "
            "Ensure LM Studio is running with the server started and at least one model loaded."
        )
    
    # Use the first discovered model for testing
    model_identifier = lmstudio_models[0]
    
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
        
        # Verify message history
        assert len(lmstudio_llm.messages) == 3  # System + User + Assistant
        assert lmstudio_llm.messages[1].content[0]["text"] == user_message.content
        assert lmstudio_llm.messages[2].content == response.content

    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server. Skipping test.")
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
        
        # Verify message history
        assert len(lmstudio_llm.messages) == 3  # System + User + Assistant
        assert lmstudio_llm.messages[1].content[0]["text"] == user_message.content
        assert lmstudio_llm.messages[2].content == complete_response

    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server. Skipping test.")
    finally:
        await lmstudio_llm.cleanup()
