import pytest
from unittest.mock import MagicMock, AsyncMock, call
from autobyteus.agent.handlers.llm_user_message_ready_event_handler import LLMUserMessageReadyEventHandler
from autobyteus.agent.events import LLMUserMessageReadyEvent
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import ChunkResponse

@pytest.fixture
def handler():
    return LLMUserMessageReadyEventHandler()

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.mark.asyncio
async def test_streaming_safe_parsing(handler, agent_context, mock_llm):
    """Test that the handler uses StreamingResponseHandler to safeguard the stream and emits PartEvents."""
    
    # Setup context
    agent_context.state.llm_instance = mock_llm
    if not isinstance(agent_context.status_manager.notifier, MagicMock):
        agent_context.status_manager.notifier = MagicMock()
        
    agent_context.input_event_queues.enqueue_internal_system_event = AsyncMock()
    
    # Setup chunks that will be fed to handler
    # The handler will feed 'content' chunks to StreamingResponseHandler
    chunks = [
        ChunkResponse(content="Hello "),
        ChunkResponse(content="World"),
        ChunkResponse(content="", reasoning="Thinking...")
    ]
    
    async def stream_gen(_):
        for c in chunks:
            yield c
            
    mock_llm.stream_user_message.side_effect = stream_gen
    
    # Trigger handle
    msg = LLMUserMessage(content="prompt")
    event = LLMUserMessageReadyEvent(llm_user_message=msg)
    
    await handler.handle(event, agent_context)
    
    # Verification
    # Since we can't easily mock the internal StreamingResponseHandler instance without patching,
    # we rely on the fact that StreamingResponseHandler (real) will process "Hello " and "World".
    # And the handler we modified has logic to emit Reasoning manually.
    
    notifier = agent_context.status_manager.notifier
    
    # Verify PartEvent notifications
    # We expect PartEvents for "Hello " and "World" (Text) and "Thinking..." (Reasoning)
    
    # Check reasoning calls (Manual emissions)
    part_event_calls = notifier.notify_agent_message_part_event.call_args_list
    
    # We should see reasoning events
    # We verify that at least one reasoning event was emitted with the correct delta
    reasoning_calls = []
    for c in part_event_calls:
        data = c[0][0]
        if data.get("event") in ("part_start", "part_delta", "part_end"):
             if data.get("part_type") == "reasoning":
                 reasoning_calls.append(data)
             elif data.get("event") == "part_delta" and "Thinking..." in data.get("delta", ""):
                 # This assumes reasoning parts reuse the delta method but we just check the content
                 reasoning_calls.append(data)

    assert len(reasoning_calls) >= 1
    
    # Check text calls (From parser)
    # The TextState emits Start, Delta, Delta...
    text_calls = []
    for c in part_event_calls:
        data = c[0][0]
        if data.get("event") in ("part_start", "part_delta") and data.get("part_type") == "text":
            text_calls.append(data)
        elif data.get("event") == "part_delta" and ("Hello" in data.get("delta", "") or "World" in data.get("delta", "")):
             text_calls.append(data)
             
    assert len(text_calls) >= 1
    
    # Verify stream end confirmation
    notifier.notify_agent_data_assistant_chunk_stream_end.assert_called_once()
    
    # Verify complete response enqueued
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()

