import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from autobyteus.agent.handlers.llm_user_message_ready_event_handler import LLMUserMessageReadyEventHandler
from autobyteus.agent.events import LLMUserMessageReadyEvent
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import ChunkResponse
from autobyteus.llm.providers import LLMProvider
from autobyteus.agent.streaming.pass_through_streaming_response_handler import PassThroughStreamingResponseHandler
from autobyteus.agent.streaming.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler

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
    mock_llm.model = MagicMock()
    mock_llm.model.provider = LLMProvider.ANTHROPIC
    agent_context.state.llm_instance = mock_llm
    # Explicitly set XML mode for this test as it verifies XML tag buffering
    agent_context.config.tool_call_format = "xml"
    # Use MagicMock because notify methods are synchronous
    if not isinstance(agent_context.status_manager.notifier, MagicMock):
        agent_context.status_manager.notifier = MagicMock()
        
    # Mock input queue for the final complete event
    # input_event_queues is a property, so we mock the method on the returned object
    agent_context.input_event_queues.enqueue_internal_system_event = AsyncMock()
    
    # Setup chunks: 
    # 1. "Hello " -> Safe text
    # 2. "<wr" -> Partial tag (should be held back)
    # 3. 'ite_file path="x">' -> Completes tag (Parsed as START, no delta)
    # 4. "World" -> Content (should be emitted)
    # 5. "</wr" -> Partial closing tag (held back)
    # 6. "ite_file>" -> Completes closing tag (Parsed as END, no delta)
    chunks = [
        ChunkResponse(content="Hello "),
        ChunkResponse(content="<wr"),
        ChunkResponse(content='ite_file path="x">'),
        ChunkResponse(content="World"),
        ChunkResponse(content="</wr"),
        ChunkResponse(content="ite_file>")
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
    assert "<wr" not in combined
    
    # Verify complete response enqueued
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()


@pytest.mark.asyncio
async def test_provider_specific_json_tool_parsing(handler, agent_context, mock_llm):
    """Handler should use provider-aware JSON parsing when JSON parser is enabled."""
    # Setup context with a Gemini provider
    mock_llm.model = MagicMock()
    mock_llm.model.provider = LLMProvider.GEMINI
    agent_context.state.llm_instance = mock_llm
    agent_context.config.tool_call_format = "json"

    if not isinstance(agent_context.status_manager.notifier, MagicMock):
        agent_context.status_manager.notifier = MagicMock()

    agent_context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
    agent_context.input_event_queues.enqueue_internal_system_event = AsyncMock()

    json_payload = '{"name": "search", "args": {"query": "autobyteus"}}'

    async def stream_gen(_):
        yield ChunkResponse(content=json_payload, is_complete=True)

    mock_llm.stream_user_message.side_effect = stream_gen

    msg = LLMUserMessage(content="prompt")
    event = LLMUserMessageReadyEvent(llm_user_message=msg)

    await handler.handle(event, agent_context)

    assert agent_context.input_event_queues.enqueue_tool_invocation_request.called
    call = agent_context.input_event_queues.enqueue_tool_invocation_request.call_args
    invocation_event = call.args[0]
    tool_invocation = invocation_event.tool_invocation
    assert tool_invocation.name == "search"
    assert tool_invocation.arguments == {"query": "autobyteus"}


@pytest.mark.asyncio
async def test_no_tools_uses_passthrough_handler(handler, agent_context, mock_llm):
    """Handler should use PassThroughStreamingResponseHandler when no tools are configured."""
    # Setup context with NO tools
    agent_context.config.tools = []
    agent_context.state.tool_instances = {}
    agent_context.state.llm_instance = mock_llm
    # PassThrough should be used regardless of mode if tools are empty, but logically mostly non-API
    agent_context.config.tool_call_format = "xml"
    
    # Mock mocks
    if not isinstance(agent_context.status_manager.notifier, MagicMock):
        agent_context.status_manager.notifier = MagicMock()
    agent_context.input_event_queues.enqueue_internal_system_event = AsyncMock()
    agent_context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()

    # Mock LLM stream
    async def stream_gen(_):
        yield ChunkResponse(content="Hello", is_complete=True)
    mock_llm.stream_user_message.side_effect = stream_gen

    msg = LLMUserMessage(content="prompt")
    event = LLMUserMessageReadyEvent(llm_user_message=msg)

    # We need to spy on the handler implementation choice
    # Since the choice happens inside the method, we can mock the class constructors 
    # in the module scope, or we can check the behavior. 
    # Checking behavior (e.g. legacy tag ignoring) is better.
    
    # Let's feed a legacy tag that PassThrough should IGNORE (treat as text)
    # whereas Parsing would catch it.
    async def stream_gen_legacy(_):
        yield ChunkResponse(content="<write_file>")
    mock_llm.stream_user_message.side_effect = stream_gen_legacy

    # Run handler
    await handler.handle(event, agent_context)

    # Verify output events
    calls = agent_context.status_manager.notifier.notify_agent_segment_event.call_args_list
    deltas = [
        call.args[0]["payload"].get("delta")
        for call in calls
        if call.args and call.args[0].get("type") == "SEGMENT_CONTENT"
    ]
    combined = "".join([d for d in deltas if isinstance(d, str)])
    
    # PassThrough should treat <write_file> as raw text
    # Parsing handler (without tools) would normally buffer it or ignore it depending on state,
    # but the key is that PassThrough guarantees it's just text.
    assert "<write_file>" in combined
    
    # AND crucially, no tool invocations should be pending
    # (Though we can't easily check internal variable, we can check queue)
    assert not agent_context.input_event_queues.enqueue_tool_invocation_request.called

@pytest.mark.asyncio
async def test_api_tool_call_handler_selection_and_schema_passing(handler, agent_context, mock_llm):
    """Handler should use ApiToolCallStreamingResponseHandler and pass schemas when tool_call_format is api_tool_call."""
    # Setup context
    agent_context.config.tool_call_format = "api_tool_call"
    tool_name = agent_context.config.tools[0].get_name()
    mock_llm.model = MagicMock()
    mock_llm.model.provider = LLMProvider.OPENAI # Explicitly set a provider
    agent_context.state.llm_instance = mock_llm
    
    # Mock mocks
    if not isinstance(agent_context.status_manager.notifier, MagicMock):
        agent_context.status_manager.notifier = MagicMock()
    agent_context.input_event_queues.enqueue_internal_system_event = AsyncMock()
    agent_context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()

    tools_schema = [{
        "type": "function",
        "function": {
            "name": tool_name,
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {"arg": {"type": "string"}},
                "required": [],
            },
        },
    }]

    # Mock LLM stream
    async def stream_gen(_, **kwargs):
        # Verify tools were passed
        assert "tools" in kwargs
        assert kwargs["tools"] == tools_schema
        yield ChunkResponse(content="Hello", is_complete=True)
        
    mock_llm.stream_user_message.side_effect = stream_gen

    # Run handler with schema provider patch
    with patch("autobyteus.agent.handlers.llm_user_message_ready_event_handler.ToolSchemaProvider") as provider_cls:
        provider_cls.return_value.build_schema.return_value = tools_schema

        msg = LLMUserMessage(content="prompt")
        event = LLMUserMessageReadyEvent(llm_user_message=msg)
        
        await handler.handle(event, agent_context)
