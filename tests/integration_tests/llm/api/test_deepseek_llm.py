
import pytest
import asyncio
import os
from autobyteus.llm.api.deepseek_llm import DeepSeekLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

@pytest.fixture
def set_deepseek_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

@pytest.fixture
def deepseek_llm(set_deepseek_env):
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        pytest.skip("DeepSeek API key not set. Skipping DeepSeekLLM tests.")
    return DeepSeekLLM(model=LLMModel.DEEPSEEK_REASONER_API)

@pytest.mark.asyncio
async def test_deepseek_llm_response(deepseek_llm):
    user_message = "Hello, DeepSeek LLM!"
    response = await deepseek_llm._send_user_message_to_llm(user_message)
    print(f"User message: {user_message}")
    
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    
    # Verify token usage if available
    if response.usage:
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0
        assert response.usage.total_tokens == (response.usage.prompt_tokens + response.usage.completion_tokens)

@pytest.mark.asyncio
async def test_deepseek_llm_streaming(deepseek_llm):
    """Test that streaming returns tokens incrementally and builds complete response"""
    user_message = "Please write a short greeting."
    received_chunks = []
    complete_response = ""
    final_usage = None
    
    async for chunk in deepseek_llm._stream_user_message_to_llm(user_message):
        assert isinstance(chunk, ChunkResponse)
        received_chunks.append(chunk)
        
        if not chunk.is_complete:
            complete_response += chunk.content
            print(f"Received token: {chunk.content}")
        else:
            final_usage = chunk.usage
    
    # Verify we received chunks
    assert len(received_chunks) > 0
    
    # Verify the complete response
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify message history was updated correctly
    assert len(deepseek_llm.messages) == 3  # System message + User message + Assistant message
    assert deepseek_llm.messages[1].content == user_message
    assert deepseek_llm.messages[2].content == complete_response

    # Verify token usage if available
    if final_usage:
        assert final_usage.prompt_tokens > 0
        assert final_usage.completion_tokens > 0
        assert final_usage.total_tokens == (final_usage.prompt_tokens + final_usage.completion_tokens)

    # Print final response for manual verification
    print(f"\nComplete response: {complete_response}")
    
    # Cleanup
    await deepseek_llm.cleanup()
