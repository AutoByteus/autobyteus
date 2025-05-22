import pytest
import asyncio
import os
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def ollama_llm():
    return LLMFactory.create_llm(model="qwen3:4b")

@pytest.mark.asyncio
async def test_ollama_llm_response(ollama_llm):
    user_message = "Hello, Ollama LLM!"
    try:
        response = await ollama_llm._send_user_message_to_llm(user_message)
        assert isinstance(response, CompleteResponse)
        assert isinstance(response.content, str)
        assert len(response.content) > 0
    except Exception as e:
        if "connection" in str(e).lower() or "ollama" in str(e).lower():
            pytest.skip("Ollama server not available. Skipping OllamaLLM tests.")
        else:
            raise

@pytest.mark.asyncio
async def test_ollama_llm_streaming(ollama_llm): 
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_tokens = []
    complete_response = ""
    
    try:
        async for token in ollama_llm._stream_user_message_to_llm(user_message):
            assert isinstance(token, ChunkResponse)
            if token.content:
                assert isinstance(token.content, str)
                received_tokens.append(token.content)
                complete_response += token.content
            
            if token.is_complete:
                if token.usage:
                    assert isinstance(token.usage, TokenUsage)
        
        assert len(received_tokens) > 0
        assert len(complete_response) > 0
        assert isinstance(complete_response, str)
        assert len(ollama_llm.messages) == 3  # System message + User message + Assistant message
    except Exception as e:
        if "connection" in str(e).lower() or "ollama" in str(e).lower():
            pytest.skip("Ollama server not available. Skipping OllamaLLM tests.")
        else:
            raise

    await ollama_llm.cleanup()

@pytest.mark.asyncio
async def test_send_user_message(ollama_llm):
    """Test the public API send_user_message"""
    user_message_text = "Can you summarize the following text?"
    user_message = LLMUserMessage(content=user_message_text)
    
    try:
        response = await ollama_llm.send_user_message(user_message)
        assert isinstance(response, str)
        assert len(response) > 0

        # Verify message history was updated correctly
        assert len(ollama_llm.messages) == 3  # System message + User message + Assistant message
        assert ollama_llm.messages[1].content == user_message_text
        assert ollama_llm.messages[2].content == response
    except Exception as e:
        if "connection" in str(e).lower() or "ollama" in str(e).lower():
            pytest.skip("Ollama server not available. Skipping OllamaLLM tests.")
        else:
            raise

@pytest.mark.asyncio
async def test_stream_user_message(ollama_llm):
    """Test the public API stream_user_message"""
    user_message_text = "Please list three benefits of using Python."
    user_message = LLMUserMessage(content=user_message_text)
    received_tokens = []
    complete_response = ""
    
    try:
        async for token in ollama_llm.stream_user_message(user_message):
            assert isinstance(token, str)
            received_tokens.append(token)
            complete_response += token
        
        assert len(received_tokens) > 0
        assert len(complete_response) > 0
        assert isinstance(complete_response, str)
        
        # Verify message history was updated correctly
        assert len(ollama_llm.messages) == 3  # System message + User message + Assistant message
        assert ollama_llm.messages[1].content == user_message_text
        assert ollama_llm.messages[2].content == complete_response
    except Exception as e:
        if "connection" in str(e).lower() or "ollama" in str(e).lower():
            pytest.skip("Ollama server not available. Skipping OllamaLLM tests.")
        else:
            raise

    await ollama_llm.cleanup()
