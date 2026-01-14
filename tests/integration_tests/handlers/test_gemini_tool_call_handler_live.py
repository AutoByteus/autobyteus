import pytest
import asyncio
import os
import json
from typing import List

from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.models import LLMModel, LLMRuntime
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.agent.streaming.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.usage.formatters.gemini_json_schema_formatter import GeminiJsonSchemaFormatter
from autobyteus.llm.utils.response_types import ChunkResponse

@pytest.fixture
def set_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY"))

@pytest.fixture
def gemini_llm(set_gemini_env):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        pytest.skip("Gemini API key not set. Skipping tests.")
    
    # Use a specific Gemini model known to support tools
    return GeminiLLM(model=LLMModel['gemini-3-flash-preview'])

@pytest.mark.asyncio
async def test_gemini_handler_live_probe(gemini_llm):
    """
    Live probe to see how Gemini streams tool calls.
    We print the raw chunks to understand the structure.
    """
    # 1. Setup Handler
    events_received: List[SegmentEvent] = []
    def on_event(event: SegmentEvent):
        events_received.append(event)
    handler = ApiToolCallStreamingResponseHandler(on_segment_event=on_event)
    
    # 2. Setup Tool
    tool_def = default_tool_registry.get_tool_definition("write_file")
    assert tool_def
    
    formatter = GeminiJsonSchemaFormatter()
    # Gemini usually expects { "function_declarations": [ ... ] } list inside "tools" config
    tool_schema = formatter.provide(tool_def)
    
    # Gemini SDK specific structure for 'tools' arg:
    # It expects a list of Tool objects or a list of Dicts (FunctionDeclarations)
    # The SDK helper typically wants: tools=[{'function_declarations': [...]}] or similar?
    # Or just a list of function declarations?
    # standard google.genai: tools=[ { "function_declarations": [ decl1, decl2 ] } ]
    # Our formatter provides a single DECLARATION dict.
    # So we wrap it.
    formatted_tools = [tool_schema]
    
    # 3. Stream from LLM
    user_message = LLMUserMessage(content="Write a python file named probe.py with content 'print(1)'")
    
    print("\nStarting Gemini stream...")
    
    chunks_received = 0
    async for chunk in gemini_llm._stream_user_message_to_llm(
        user_message,
        tools=formatted_tools 
    ):
        chunks_received += 1
        print(f"CHUNK {chunks_received}: content='{chunk.content}' tool_calls={chunk.tool_calls}")
        handler.feed(chunk)
        
    handler.finalize()
    
    # 4. Verify
    invocations = handler.get_all_invocations()
    print(f"Invocations: {invocations}")
    
    assert len(invocations) > 0
    assert invocations[0].name == "write_file"

    await gemini_llm.cleanup()
