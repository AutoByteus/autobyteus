import pytest
import asyncio
import os
import json
from typing import List

from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.agent.streaming.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from autobyteus.agent.streaming.parser.events import SegmentEvent
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.usage.formatters.mistral_json_schema_formatter import MistralJsonSchemaFormatter
from autobyteus.llm.utils.response_types import ChunkResponse

@pytest.fixture
def set_mistral_env(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", os.getenv("MISTRAL_API_KEY", "YOUR_API_KEY"))

@pytest.fixture
def mistral_llm(set_mistral_env):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY":
        pytest.skip("MISTRAL_API_KEY not set. Skipping tests.")
    
    # Use mistral-large-latest or similar
    return MistralLLM(model=LLMModel['mistral-large'])

@pytest.mark.asyncio
async def test_mistral_handler_integrates_with_live_stream(mistral_llm):
    """
    Verifies that the ApiToolCallStreamingResponseHandler correctly processes
    a live stream from Mistral, accumulating deltas and emitting events.
    """
    
    # 1. Setup Handler
    events_received: List[SegmentEvent] = []
    def on_event(event: SegmentEvent):
        events_received.append(event)
        print(f"Event: {event}")

    handler = ApiToolCallStreamingResponseHandler(on_segment_event=on_event)
    
    # 2. Setup Tool
    tool_def = default_tool_registry.get_tool_definition("write_file")
    assert tool_def
    
    formatter = MistralJsonSchemaFormatter()
    tool_schema = formatter.provide(tool_def)
    
    # 3. Stream from LLM
    # Request a tool call
    user_message = LLMUserMessage(content="Write a python file named mistral_test.py with content 'print(1)'")
    
    print("\nStarting Mistral stream...")
    
    chunks_received = 0
    # Feed chunks to handler
    async for chunk in mistral_llm._stream_user_message_to_llm(
        user_message,
        tools=[tool_schema]
    ):
        chunks_received += 1
        # handler.feed() handles tool_calls in the chunk
        handler.feed(chunk)

    # 4. Finalize
    handler.finalize()
    
    # 5. Verify Metadata and Invocations
    print(f"Total events received: {len(events_received)}")
    
    # Check for ToolInvocation
    invocations = handler.get_all_invocations()
    assert len(invocations) == 1, "Expected exactly one ToolInvocation"
    
    invocation = invocations[0]
    print(f"Verified ToolInvocation: {invocation}")
    
    assert invocation.name == "write_file"
    assert invocation.arguments
    assert "path" in invocation.arguments
    assert "content" in invocation.arguments
    assert invocation.arguments["path"] == "mistral_test.py"
    assert invocation.id is not None

    await mistral_llm.cleanup()
