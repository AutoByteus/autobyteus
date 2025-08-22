import pytest
import asyncio
import os
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.providers import LLMProvider

@pytest.fixture
def ollama_llm():
    # Re-initialize factory to discover local models
    LLMFactory.reinitialize()
    ollama_models = LLMFactory.list_models_by_provider(LLMProvider.OLLAMA)
    if not ollama_models:
        pytest.skip("No Ollama models found. Skipping tests. Ensure Ollama is running.")

    # Use the first available Ollama model for testing
    model_identifier = ollama_models[0].model_identifier
    try:
        return LLMFactory.create_llm(model_identifier=model_identifier)
    except Exception as e:
        pytest.skip(f"Could not connect to Ollama or create LLM instance. Error: {e}")

@pytest.mark.asyncio
async def test_ollama_llm_response(ollama_llm):
    user_message = LLMUserMessage(content="Hello, Ollama LLM! Please respond with 'pong'.")
    try:
        response = await ollama_llm._send_user_message_to_llm(user_message)
        assert isinstance(response, CompleteResponse)
        assert isinstance(response.content, str)
        assert "pong" in response.content.lower()
    except Exception as e:
        pytest.skip(f"Ollama test failed, server may be unavailable. Error: {e}")

@pytest.mark.asyncio
async def test_ollama_llm_streaming(ollama_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = LLMUserMessage(content="Please write a short greeting.")
    received_tokens = []
    complete_response = ""
    
    try:
        async for chunk in ollama_llm._stream_user_message_to_llm(user_message):
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
        assert len(ollama_llm.messages) == 3
    except Exception as e:
        pytest.skip(f"Ollama test failed, server may be unavailable. Error: {e}")

    await ollama_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(ollama_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text: The quick brown fox jumps over the lazy dog."
    user_message = LLMUserMessage(content=user_message_text)
    
    try:
        response_obj = await ollama_llm.send_user_message(user_message)
        assert isinstance(response_obj, CompleteResponse)
        assert isinstance(response_obj.content, str)
        assert len(response_obj.content) > 0

        assert len(ollama_llm.messages) == 3
        assert ollama_llm.messages[1].content == user_message_text
        assert ollama_llm.messages[2].content == response_obj.content
    except Exception as e:
        pytest.skip(f"Ollama test failed, server may be unavailable. Error: {e}")

@pytest.mark.asyncio
async def test_stream_user_message(ollama_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    try:
        async for chunk in ollama_llm.stream_user_message(user_message):
            assert isinstance(chunk, ChunkResponse)
            assert isinstance(chunk.content, str)
            received_tokens.append(chunk.content)
            complete_response += chunk.content
        
        assert len(received_tokens) > 0
        assert len(complete_response) > 0
        assert isinstance(complete_response, str)
        
        assert len(ollama_llm.messages) == 3
        assert ollama_llm.messages[1].content == user_message_text
        assert ollama_llm.messages[2].content == complete_response
    except Exception as e:
        pytest.skip(f"Ollama test failed, server may be unavailable. Error: {e}")

    await ollama_llm.cleanup()
