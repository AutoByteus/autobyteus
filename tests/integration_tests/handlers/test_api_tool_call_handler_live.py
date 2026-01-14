import pytest
import asyncio
import os
import json
from typing import List

from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel, LLMRuntime
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.agent.streaming.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.usage.formatters.openai_json_schema_formatter import OpenAiJsonSchemaFormatter

@pytest.fixture
def set_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))

@pytest.fixture
def openai_llm(set_openai_env):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key or openai_api_key == "YOUR_OPENAI_API_KEY":
        pytest.skip("OpenAI API key not set. Skipping tests.")
    
    # Use generic model if available, or fallback to known identifier
    # Trying to reuse logic from typical tests
    return OpenAILLM(model=LLMModel['gpt-5.2'])

@pytest.mark.asyncio
async def test_handler_integrates_with_live_stream(openai_llm):
    """
    Integration test verifying that ApiToolCallStreamingResponseHandler
    correctly processes a live stream from OpenAI Compatible LLM.
    """
    # 1. Setup Handler
    events_received: List[SegmentEvent] = []
    
    def on_event(event: SegmentEvent):
        events_received.append(event)
        
    handler = ApiToolCallStreamingResponseHandler(on_segment_event=on_event)
    
    # 2. Setup Tool
    tool_def = default_tool_registry.get_tool_definition("write_file")
    assert tool_def
    
    formatter = OpenAiJsonSchemaFormatter()
    tools_schema = [formatter.provide(tool_def)]
    
    # 3. Stream from LLM
    user_message = LLMUserMessage(content="Write a python file named hello.py with content 'print(1)'")
    
    print("\nStarting stream...")
    async for chunk in openai_llm._stream_user_message_to_llm(
        user_message,
        tools=tools_schema
    ):
        # Feed chunk to handler
        handler.feed(chunk)
        
    # 4. Finalize
    handler.finalize()
    
    # 5. Verification
    print(f"Total events received: {len(events_received)}")
    
    # We expect:
    # - SEGMENT_START (type=TOOL_CALL)
    # - Multiple SEGMENT_CONTENT (streaming args)
    # - SEGMENT_END (with parsed metadata)
    
    tool_starts = [e for e in events_received if e.event_type == SegmentEventType.START and e.segment_type == SegmentType.TOOL_CALL]
    assert len(tool_starts) >= 1, "Expected at least one tool call start event"
    
    start_event = tool_starts[0]
    assert start_event.payload.get("metadata", {}).get("tool_name") == "write_file"
    segment_id = start_event.segment_id
    
    # Check end event for this segment
    end_event = next((e for e in events_received if e.event_type == SegmentEventType.END and e.segment_id == segment_id), None)
    assert end_event, "Expected end event for tool call"
    
    # Verify metadata contains accumulated arguments
    metadata = end_event.payload.get("metadata", {})
    assert "arguments" in metadata
    args = metadata["arguments"]
    
    print(f"Final Parsed Arguments: {args}")
    
    assert isinstance(args, dict)
    assert "filename" in args or "path" in args  # 'write_file' uses 'filename' or 'path' depending on definition
    # Our mocked tool def usually has 'filename' or 'file_path'
    # Let's check keys loosely or check content
    assert any(k in args for k in ["filename", "file_path", "path"]), f"Expected filename arg, got {args.keys()}"
    assert "content" in args
    assert "print(1)" in args["content"]

    # 6. Verify ToolInvocation (Crucial Step)
    invocations = handler.get_all_invocations()
    assert len(invocations) == 1, "Expected exactly one ToolInvocation"
    
    invocation = invocations[0]
    assert invocation.name == "write_file"
    assert invocation.arguments == args  # Invocation args should match parsed metadata args
    assert invocation.id is not None # Should match the call_id from stream

    print(f"Verified ToolInvocation: {invocation}")

    await openai_llm.cleanup()
