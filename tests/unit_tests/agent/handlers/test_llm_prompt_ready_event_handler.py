import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, call

from autobyteus.agent.handlers.llm_prompt_ready_event_handler import LLMPromptReadyEventHandler
from autobyteus.agent.events.agent_events import LLMPromptReadyEvent, LLMCompleteResponseReceivedEvent
from autobyteus.agent.events.agent_event_queues import END_OF_STREAM_SENTINEL
from autobyteus.llm.user_message import LLMUserMessage


@pytest.fixture
def llm_prompt_ready_handler():
    return LLMPromptReadyEventHandler()

@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_success_stream(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    """Test successful handling of LLMPromptReadyEvent with LLM streaming."""
    user_content = "Tell me a joke."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    # Mock LLM stream
    mock_stream_chunks = ["Why ", "don't ", "scientists ", "trust ", "atoms? ", "Because ", "they ", "make ", "up ", "everything!"]
    
    async def mock_llm_stream_generator(*args, **kwargs):
        for chunk in mock_stream_chunks:
            yield chunk # Simulate simple string chunks for this test
            await asyncio.sleep(0) # Yield control

    agent_context.llm_instance.stream_user_message = AsyncMock(side_effect=mock_llm_stream_generator)

    with caplog.at_level(logging.INFO):
        await llm_prompt_ready_handler.handle(event, agent_context)

    # Check logs
    assert f"Agent '{agent_context.agent_id}' handling LLMPromptReadyEvent: '{user_content[:100]}...'" in caplog.text
    assert f"Agent '{agent_context.agent_id}' LLM stream completed." in caplog.text
    assert f"Agent '{agent_context.agent_id}' enqueued LLMCompleteResponseReceivedEvent from LLMPromptReadyEventHandler." in caplog.text

    # Check history update (user message)
    agent_context.add_message_to_history.assert_any_call({"role": "user", "content": user_content})

    # Check assistant output chunk queue
    expected_chunk_calls = [call(chunk) for chunk in mock_stream_chunks] + [call(END_OF_STREAM_SENTINEL)]
    agent_context.queues.assistant_output_chunk_queue.put.assert_has_calls(expected_chunk_calls, any_order=False)
    
    # Check history update (assistant response)
    full_response = "".join(mock_stream_chunks)
    agent_context.add_message_to_history.assert_any_call({"role": "assistant", "content": full_response})
    
    # Check enqueued LLMCompleteResponseReceivedEvent
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMCompleteResponseReceivedEvent)
    assert enqueued_event.complete_response_text == full_response
    assert not enqueued_event.is_error


@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_llm_stream_error(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    """Test handling when the LLM stream itself raises an exception."""
    user_content = "This will cause an error."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    llm_error_message = "LLM simulated error"
    
    async def erroring_llm_stream_generator(*args, **kwargs):
        yield "First part, "
        await asyncio.sleep(0)
        raise ValueError(llm_error_message)
        yield "this won't be yielded." # pragma: no cover

    agent_context.llm_instance.stream_user_message = AsyncMock(side_effect=erroring_llm_stream_generator)

    with caplog.at_level(logging.ERROR): # Capture ERROR for the LLM stream error
        await llm_prompt_ready_handler.handle(event, agent_context)

    # Check logs
    assert f"Agent '{agent_context.agent_id}' error during LLM stream: {llm_error_message}" in caplog.text
    assert f"Agent '{agent_context.agent_id}' enqueued LLMCompleteResponseReceivedEvent with error details" in caplog.text

    # Check history (user message, then assistant error message)
    agent_context.add_message_to_history.assert_any_call({"role": "user", "content": user_content})
    
    expected_error_output = f"Error processing your request with the LLM: {llm_error_message}"
    agent_context.add_message_to_history.assert_any_call({"role": "assistant", "content": expected_error_output, "is_error": True})

    # Check chunk queue (should get END_OF_STREAM_SENTINEL after error)
    # It might have received "First part, " before the error
    agent_context.queues.assistant_output_chunk_queue.put.assert_any_call("First part, ")
    agent_context.queues.assistant_output_chunk_queue.put.assert_any_call(END_OF_STREAM_SENTINEL)
    
    # Check enqueued LLMCompleteResponseReceivedEvent (should be an error event)
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMCompleteResponseReceivedEvent)
    assert enqueued_event.complete_response_text == expected_error_output
    assert enqueued_event.is_error

@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_chunk_queue_full(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    """Test behavior when the assistant_output_chunk_queue is full during an LLM error."""
    user_content = "Content causing queue full on error."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    llm_error_message = "LLM error with full queue"
    
    async def erroring_llm_stream_generator(*args, **kwargs):
        raise RuntimeError(llm_error_message) # Error happens immediately

    agent_context.llm_instance.stream_user_message = AsyncMock(side_effect=erroring_llm_stream_generator)
    # Simulate a full queue
    agent_context.queues.assistant_output_chunk_queue.full = MagicMock(return_value=True)
    # Ensure put still works for the test of not placing sentinel
    agent_context.queues.assistant_output_chunk_queue.put = AsyncMock()


    with caplog.at_level(logging.WARNING): # Capture WARNING for full queue
        await llm_prompt_ready_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' chunk_queue is full, cannot place error sentinel." in caplog.text
    
    # Ensure END_OF_STREAM_SENTINEL was not put on the (mocked full) chunk_queue
    # We check that `put` was not called with the sentinel.
    # If `put` was called for other reasons (e.g. earlier chunks before error), that's fine.
    # In this specific test, error happens immediately, so `put` should not be called at all on chunk queue.
    
    sentinel_not_called_on_chunk_queue = True
    for call_item in agent_context.queues.assistant_output_chunk_queue.put.call_args_list:
        if call_item[0][0] == END_OF_STREAM_SENTINEL:
            sentinel_not_called_on_chunk_queue = False # pragma: no cover
            break
    assert sentinel_not_called_on_chunk_queue

    # Verify other error handling aspects (history, enqueued error event)
    expected_error_output = f"Error processing your request with the LLM: {llm_error_message}"
    agent_context.add_message_to_history.assert_any_call({"role": "assistant", "content": expected_error_output, "is_error": True})
    
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert enqueued_event.complete_response_text == expected_error_output
    assert enqueued_event.is_error

def test_llm_prompt_ready_handler_initialization(caplog):
    """Test initialization of the handler."""
    with caplog.at_level(logging.INFO):
        handler = LLMPromptReadyEventHandler()
    assert "LLMPromptReadyEventHandler initialized." in caplog.text

@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_llm_stream_chunk_is_object(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    """Test when LLM stream yields objects with a 'content' attribute."""
    user_content = "Test with object chunks."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    class MockChunkObject:
        def __init__(self, content_str):
            self.content = content_str
        def __str__(self): # pragma: no cover
            return f"MockChunkObject(content='{self.content}')"


    mock_stream_chunks_obj = [MockChunkObject("Part 1"), MockChunkObject(" and Part 2")]
    
    async def mock_llm_stream_obj_generator(*args, **kwargs):
        for chunk_obj in mock_stream_chunks_obj:
            yield chunk_obj
            await asyncio.sleep(0)

    agent_context.llm_instance.stream_user_message = AsyncMock(side_effect=mock_llm_stream_obj_generator)

    await llm_prompt_ready_handler.handle(event, agent_context)

    expected_content_parts = [obj.content for obj in mock_stream_chunks_obj]
    full_response = "".join(expected_content_parts)

    # Check chunk queue (should receive the string content of each object)
    expected_chunk_calls = [call(part) for part in expected_content_parts] + [call(END_OF_STREAM_SENTINEL)]
    agent_context.queues.assistant_output_chunk_queue.put.assert_has_calls(expected_chunk_calls, any_order=False)
    
    # Check enqueued LLMCompleteResponseReceivedEvent
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert enqueued_event.complete_response_text == full_response

@pytest.mark.asyncio
async def test_handle_llm_prompt_ready_llm_stream_chunk_is_unexpected_type(llm_prompt_ready_handler: LLMPromptReadyEventHandler, agent_context, caplog):
    """Test when LLM stream yields unexpected chunk types (logged as warning)."""
    user_content = "Test with unexpected chunk type."
    llm_user_message = LLMUserMessage(content=user_content)
    event = LLMPromptReadyEvent(llm_user_message=llm_user_message)

    mock_stream_unexpected_chunks = [123, {"key": "val"}] # int and dict
    
    async def mock_llm_stream_unexpected_generator(*args, **kwargs):
        for chunk_item in mock_stream_unexpected_chunks:
            yield chunk_item
            await asyncio.sleep(0)

    agent_context.llm_instance.stream_user_message = AsyncMock(side_effect=mock_llm_stream_unexpected_generator)

    with caplog.at_level(logging.WARNING): # Capture warnings
        await llm_prompt_ready_handler.handle(event, agent_context)

    # Check for warnings about unexpected chunk types
    assert f"Agent '{agent_context.agent_id}' received unexpected chunk type: <class 'int'>" in caplog.text
    assert f"Agent '{agent_context.agent_id}' received unexpected chunk type: <class 'dict'>" in caplog.text

    # Check that stringified versions were put on queue
    expected_str_chunks = [str(item) for item in mock_stream_unexpected_chunks]
    full_response_str = "".join(expected_str_chunks)
    
    expected_chunk_calls = [call(s_chunk) for s_chunk in expected_str_chunks] + [call(END_OF_STREAM_SENTINEL)]
    agent_context.queues.assistant_output_chunk_queue.put.assert_has_calls(expected_chunk_calls, any_order=False)
    
    # Check enqueued LLMCompleteResponseReceivedEvent
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert enqueued_event.complete_response_text == full_response_str

