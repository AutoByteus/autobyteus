
import pytest
import asyncio
import os
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.utils.token_usage import TokenUsage

@pytest.fixture
def set_claude_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

@pytest.fixture
def claude_llm(set_claude_env):
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        pytest.skip("Anthropic API key not set. Skipping ClaudeLLM tests.")
    system_message = "You are a helpful assistant."
    return ClaudeLLM(model=LLMModel.CLAUDE_3_5_SONNET_API, system_message=system_message)

@pytest.mark.asyncio
async def test_claude_llm_response(claude_llm):
    """Test non-streaming response with token usage tracking"""
    user_message = "Hello, Claude LLM!"
    response = await claude_llm._send_user_message_to_llm(user_message)
    
    # Verify response type and content
    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    
    # Verify token usage
    assert isinstance(response.usage, TokenUsage)
    assert response.usage.prompt_tokens > 0
    assert response.usage.completion_tokens > 0
    assert response.usage.total_tokens == response.usage.prompt_tokens + response.usage.completion_tokens
    
    # Print usage stats for debugging
    print(f"\nToken Usage:")
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    print(f"Total tokens: {response.usage.total_tokens}")
    
    # Verify message history
    assert len(claude_llm.messages) == 3  # System + User + Assistant
    assert claude_llm.messages[1].content == user_message
    assert claude_llm.messages[2].content == response.content

@pytest.mark.asyncio
async def test_claude_llm_streaming(claude_llm):
    """Test streaming response with token usage tracking and event logging"""
    user_message = "Please write a short greeting."
    received_chunks = []
    complete_response = ""
    final_usage = None
    
    async for chunk in claude_llm._stream_user_message_to_llm(user_message):
        # Verify chunk type and structure
        assert isinstance(chunk, ChunkResponse)
        
        # Store chunk content
        received_chunks.append(chunk)
        if not chunk.is_complete:
            complete_response += chunk.content
            # Print tokens as they arrive for debugging
            print(f"Received chunk: {chunk.content}")
        else:
            # Last chunk should contain usage information
            assert chunk.usage is not None
            final_usage = chunk.usage
            print("\nFinal chunk received with token usage")
    
    # Verify we received chunks
    assert len(received_chunks) > 0
    
    # Verify the complete response
    assert len(complete_response) > 0
    assert isinstance(complete_response, str)
    
    # Verify token usage in final chunk
    assert final_usage is not None
    assert isinstance(final_usage, TokenUsage)
    assert final_usage.prompt_tokens > 0
    assert final_usage.completion_tokens > 0
    assert final_usage.total_tokens == final_usage.prompt_tokens + final_usage.completion_tokens
    
    # Print token usage for debugging
    print(f"\nToken Usage:")
    print(f"Prompt tokens: {final_usage.prompt_tokens}")
    print(f"Completion tokens: {final_usage.completion_tokens}")
    print(f"Total tokens: {final_usage.total_tokens}")
    
    # Verify message history was updated correctly
    assert len(claude_llm.messages) == 3  # System + User + Assistant
    assert claude_llm.messages[1].content == user_message
    assert claude_llm.messages[2].content == complete_response
    
    # Print final response for manual verification
    print(f"\nComplete response: {complete_response}")

@pytest.mark.asyncio
async def test_claude_llm_token_usage_consistency(claude_llm):
    """Test that token usage is consistent between streaming and non-streaming modes"""
    user_message = "Write a one-sentence greeting."
    
    # Get non-streaming response
    non_streaming_response = await claude_llm._send_user_message_to_llm(user_message)
    non_streaming_usage = non_streaming_response.usage
    
    await claude_llm.cleanup()
    
    # Get streaming response
    streaming_final_usage = None
    async for chunk in claude_llm._stream_user_message_to_llm(user_message):
        if chunk.is_complete:
            streaming_final_usage = chunk.usage
    
    # Verify both modes provide token usage
    assert non_streaming_usage is not None
    assert streaming_final_usage is not None
    
    # Print usage comparison for debugging
    print("\nToken Usage Comparison:")
    print("Non-streaming:")
    print(f"Prompt tokens: {non_streaming_usage.prompt_tokens}")
    print(f"Completion tokens: {non_streaming_usage.completion_tokens}")
    print(f"Total tokens: {non_streaming_usage.total_tokens}")
    print("\nStreaming:")
    print(f"Prompt tokens: {streaming_final_usage.prompt_tokens}")
    print(f"Completion tokens: {streaming_final_usage.completion_tokens}")
    print(f"Total tokens: {streaming_final_usage.total_tokens}")
    
    # Verify token usage structure is consistent
    assert isinstance(non_streaming_usage.prompt_tokens, int)
    assert isinstance(streaming_final_usage.prompt_tokens, int)
    assert isinstance(non_streaming_usage.completion_tokens, int)
    assert isinstance(streaming_final_usage.completion_tokens, int)
    assert isinstance(non_streaming_usage.total_tokens, int)
    assert isinstance(streaming_final_usage.total_tokens, int)

@pytest.mark.asyncio
async def test_cleanup(claude_llm):
    """Test cleanup functionality"""
    # Add some messages
    await claude_llm._send_user_message_to_llm("Hello")
    
    # Verify messages exist
    assert len(claude_llm.messages) > 0
    
    # Cleanup
    await claude_llm.cleanup()
    
    # Verify messages were cleared
    assert len(claude_llm.messages) == 0
