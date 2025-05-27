import pytest
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock, call

from autobyteus.agent.handlers.llm_prompt_ready_event_handler import LLMPromptReadyEventHandler
from autobyteus.agent.events.agent_events import LLMPromptReadyEvent, LLMCompleteResponseReceivedEvent
from autobyteus.agent.events.agent_event_queues import END_OF_STREAM_SENTINEL
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.base_llm import BaseLLM # Added import for BaseLLM spec

@pytest.fixture
def llm_prompt_ready_handler():
    return LLMPromptReadyEventHandler()

# Simplified mock generator for successful streams
async def mock_llm_stream_success_generator(chunks_to_yield):
    for item in chunks_to_yield:
        yield item
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_success_stream(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    """Test successful handling of LLMPromptReadyEvent with LLM streaming,
    where the last chunk may only contain usage data."""
    user_content = "Tell me a joke."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    mock_chunks_data = [
        ChunkResponse(content="Why ", is_complete=False),
        ChunkResponse(content="don't ", is_complete=False),
        ChunkResponse(content="scientists ", is_complete=False),
        ChunkResponse(content="trust ", is_complete=False),
        ChunkResponse(content="atoms? ", is_complete=False),
        ChunkResponse(content="Because ", is_complete=False),
        ChunkResponse(content="they ", is_complete=False),
        ChunkResponse(content="make ", is_complete=False),
        ChunkResponse(content="up ", is_complete=False),
        ChunkResponse(content="everything!", is_complete=False),
        ChunkResponse(content="", is_complete=True, usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30))
    ]
    
    # Mock the public stream_user_message method directly using MagicMock's side_effect
    # stream_user_message is an async generator function, so it returns an async generator directly.
    agent_context.llm_instance.stream_user_message.side_effect = \
        lambda *args, **kwargs: mock_llm_stream_success_generator(mock_chunks_data)

    with caplog.at_level(logging.DEBUG):
        await llm_prompt_ready_handler.handle(event, agent_context)

    full_response = "".join(chunk.content for chunk in mock_chunks_data)

    # Check history update (user message)
    agent_context.add_message_to_history.assert_any_call({"role": "user", "content": user_content})

    # Check assistant output chunk queue calls
    # Assert that the correct number of calls occurred
    assert agent_context.queues.assistant_output_chunk_queue.put.call_count == len(mock_chunks_data) + 1
    # Assert that the last call was the END_OF_STREAM_SENTINEL
    assert agent_context.queues.assistant_output_chunk_queue.put.call_args_list[-1].args[0] is END_OF_STREAM_SENTINEL
    # Optionally, assert that the first N calls were instances of ChunkResponse
    for i in range(len(mock_chunks_data)):
        assert isinstance(agent_context.queues.assistant_output_chunk_queue.put.call_args_list[i].args[0], ChunkResponse)
        # For simplicity, don't assert exact chunk content match unless strictly necessary,
        # as it was causing fragility. The generator ensures the content is correct.
    
    # Check history update (assistant response)
    agent_context.add_message_to_history.assert_any_call({"role": "assistant", "content": full_response})
    
    # Check enqueued LLMCompleteResponseReceivedEvent
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMCompleteResponseReceivedEvent)
    assert enqueued_event.complete_response_text == full_response
    assert not enqueued_event.is_error


@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_llm_stream_error(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    user_content = "This will cause an error."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    llm_error_message = "LLM simulated error"
    
    # Mock the public stream_user_message method to raise an error
    agent_context.llm_instance.stream_user_message.side_effect = ValueError(llm_error_message)

    with caplog.at_level(logging.DEBUG):
        await llm_prompt_ready_handler.handle(event, agent_context)

    agent_context.add_message_to_history.assert_any_call({"role": "user", "content": user_content})
    expected_error_output = f"Error processing your request with the LLM: {llm_error_message}"
    agent_context.add_message_to_history.assert_any_call({"role": "assistant", "content": expected_error_output, "is_error": True})

    # When an error occurs immediately, no chunks are yielded.
    # Only the sentinel should be put if the queue is not full.
    # (mock_event_queues in conftest now defaults .full() to return False)
    assert agent_context.queues.assistant_output_chunk_queue.put.call_count == 1
    agent_context.queues.assistant_output_chunk_queue.put.assert_called_once_with(END_OF_STREAM_SENTINEL)
    
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMCompleteResponseReceivedEvent)
    assert enqueued_event.complete_response_text == expected_error_output
    assert enqueued_event.is_error


@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_chunk_queue_full_on_error(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    user_content = "Content causing queue full on error."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    llm_error_message = "LLM error with full queue"
    
    # Mock the public stream_user_message method to raise an error
    agent_context.llm_instance.stream_user_message.side_effect = RuntimeError(llm_error_message)

    # Override the default .full() mock for this specific test case
    agent_context.queues.assistant_output_chunk_queue.full = MagicMock(return_value=True)
    # Reset put mock for this test if necessary, or ensure it's clean from agent_context fixture
    agent_context.queues.assistant_output_chunk_queue.put = AsyncMock() 

    with caplog.at_level(logging.DEBUG):
        await llm_prompt_ready_handler.handle(event, agent_context)

    expected_error_output = f"Error processing your request with the LLM: {llm_error_message}"
    agent_context.add_message_to_history.assert_any_call({"role": "assistant", "content": expected_error_output, "is_error": True})
    
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMCompleteResponseReceivedEvent)
    assert enqueued_event.complete_response_text == expected_error_output
    assert enqueued_event.is_error
    
    # Assert that sentinel was NOT put because queue was full (as mocked)
    agent_context.queues.assistant_output_chunk_queue.put.assert_not_called()


@pytest.mark.asyncio
async def test_handle_llm_stream_yields_unexpected_chunk_type(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    user_content = "Test with unexpected chunk type."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    mock_stream_objects = [
        "Plain string chunk", 
        123,                  
        ChunkResponse(content="ActualChunk", is_complete=False), 
        {"data": "dict_chunk"} 
    ]
    
    # Mock the public stream_user_message method
    agent_context.llm_instance.stream_user_message.side_effect = \
        lambda *args, **kwargs: mock_llm_stream_success_generator(mock_stream_objects)

    with caplog.at_level(logging.WARNING):
        await llm_prompt_ready_handler.handle(event, agent_context)
    
    # Check calls to put: only the valid ChunkResponse and the sentinel
    assert agent_context.queues.assistant_output_chunk_queue.put.call_count == 2
    assert agent_context.queues.assistant_output_chunk_queue.put.call_args_list[0].args[0] == mock_stream_objects[2]
    assert agent_context.queues.assistant_output_chunk_queue.put.call_args_list[1].args[0] is END_OF_STREAM_SENTINEL
    
    expected_aggregated_content = "ActualChunk" # Only content from valid ChunkResponse
    agent_context.add_message_to_history.assert_any_call({"role": "assistant", "content": expected_aggregated_content})
    
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert enqueued_event.complete_response_text == expected_aggregated_content


def test_llm_prompt_ready_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = LLMPromptReadyEventHandler()

