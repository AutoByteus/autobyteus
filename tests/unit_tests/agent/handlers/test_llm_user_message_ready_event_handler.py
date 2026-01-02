import pytest
from unittest.mock import MagicMock, AsyncMock
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
    """Test that the handler uses StreamingResponseHandler to safeguard the stream."""
    
    # Setup context
    agent_context.state.llm_instance = mock_llm
    # Use MagicMock because notify methods are synchronous
    if not isinstance(agent_context.status_manager.notifier, MagicMock):
        agent_context.status_manager.notifier = MagicMock()
        
    # Mock input queue for the final complete event
    # input_event_queues is a property, so we mock the method on the returned object
    agent_context.input_event_queues.enqueue_internal_system_event = AsyncMock()
    
    # Setup chunks: 
    # 1. "Hello " -> Safe text
    # 2. "<fi" -> Partial tag (should be held back)
    # 3. 'le path="x">' -> Completes tag (Parsed as START, no delta)
    # 4. "World" -> Content (should be emitted)
    # 5. "</fi" -> Partial closing tag (held back)
    # 6. "le>" -> Completes closing tag (Parsed as END, no delta)
    chunks = [
        ChunkResponse(content="Hello "),
        ChunkResponse(content="<fi"),
        ChunkResponse(content='le path="x">'),
        ChunkResponse(content="World"),
        ChunkResponse(content="</fi"),
        ChunkResponse(content="le>")
    ]
    
    async def stream_gen(_):
        for c in chunks:
            yield c
            
    mock_llm.stream_user_message.side_effect = stream_gen
    
    # Create event
    msg = LLMUserMessage(content="prompt")
    event = LLMUserMessageReadyEvent(llm_user_message=msg)
    
    await handler.handle(event, agent_context)
    
    # Verify segment events were emitted with safe deltas
    calls = agent_context.status_manager.notifier.notify_agent_segment_event.call_args_list
    deltas = [
        call.args[0]["payload"].get("delta")
        for call in calls
        if call.args and call.args[0].get("type") == "SEGMENT_CONTENT"
    ]
    combined = "".join([d for d in deltas if isinstance(d, str)])
    assert "Hello " in combined
    assert "World" in combined
    assert "<fi" not in combined
    
    # Verify complete response enqueued
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
