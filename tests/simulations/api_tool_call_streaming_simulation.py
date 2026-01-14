#!/usr/bin/env python3
"""
End-to-End Runtime Simulation: API Tool Call Streaming Design Validation (v2)

This version validates the UNIFIED architecture where:
1. Handler ONLY emits SegmentEvents (single responsibility)
2. ToolInvocationAdapter creates ToolInvocations from events (unified path)
3. API tool calls pass pre-parsed arguments via SEGMENT_END metadata

Run with: uv run python tests/simulations/api_tool_call_streaming_simulation.py
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# SECTION 1: Imports from Codebase
# =============================================================================

from autobyteus.llm.utils.tool_call_delta import ToolCallDelta
from autobyteus.llm.utils.response_types import ChunkResponse
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.streaming.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from autobyteus.agent.streaming.parser.invocation_adapter import ToolInvocationAdapter

# =============================================================================
# SECTION 2: OpenAI Tool Call Converter (Keep Mock for Simulation)
# =============================================================================

@dataclass
class MockOpenAIFunction:
    """Simulates OpenAI SDK's ChoiceDeltaToolCallFunction"""
    name: Optional[str] = None
    arguments: Optional[str] = None


@dataclass
class MockOpenAIToolCall:
    """Simulates OpenAI SDK's ChoiceDeltaToolCall"""
    index: int
    id: Optional[str] = None
    function: Optional[MockOpenAIFunction] = None


def openai_tool_call_converter(delta_tool_calls: Optional[List[MockOpenAIToolCall]]) -> Optional[List[ToolCallDelta]]:
    """Convert OpenAI SDK tool call deltas to normalized ToolCallDelta objects."""
    if not delta_tool_calls:
        return None
    
    result = []
    for tc in delta_tool_calls:
        result.append(ToolCallDelta(
            index=tc.index,
            call_id=tc.id if tc.id else None,
            name=tc.function.name if tc.function and tc.function.name else None,
            arguments_delta=tc.function.arguments if tc.function and tc.function.arguments else None,
        ))
    return result


# =============================================================================
# SECTION 7: End-to-End Simulation
# =============================================================================

def simulate_openai_stream():
    """Simulates OpenAI SDK streaming with tool calls."""
    
    yield MockOpenAIToolCall(index=-1), "Sure, I'll create that file for you."
    yield MockOpenAIToolCall(index=-1), " Let me write it now."
    
    yield MockOpenAIToolCall(
        index=0,
        id="call_abc123",
        function=MockOpenAIFunction(name="write_file", arguments="")
    ), None
    
    yield MockOpenAIToolCall(
        index=0,
        function=MockOpenAIFunction(arguments='{"path": ')
    ), None
    
    yield MockOpenAIToolCall(
        index=0,
        function=MockOpenAIFunction(arguments='"hello.py"')
    ), None
    
    yield MockOpenAIToolCall(
        index=0,
        function=MockOpenAIFunction(arguments=', "content":')
    ), None
    
    yield MockOpenAIToolCall(
        index=0,
        function=MockOpenAIFunction(arguments=' "print(\'Hello World\')"}')
    ), None


def run_unified_simulation():
    """Run the unified architecture simulation using REAL classes."""
    print("=" * 80)
    print("UNIFIED API TOOL CALL STREAMING - END-TO-END SIMULATION (REAL IMPLEMENTATION)")
    print("=" * 80)
    print()
    
    all_emitted_events = []
    
    def on_segment_event(event: SegmentEvent):
        all_emitted_events.append(event)
    
    # Create handler (Using REAL class)
    handler = ApiToolCallStreamingResponseHandler(
        on_segment_event=on_segment_event,
        segment_id_prefix="sim_"
    )
    
    print("STEP 1: Streaming Chunks → Handler")
    print("-" * 40)
    
    chunk_num = 0
    
    for openai_tool_call, text_content in simulate_openai_stream():
        chunk_num += 1
        
        tool_calls_raw = None
        if openai_tool_call.index >= 0:
            tool_calls_raw = [openai_tool_call]
        
        tool_call_deltas = openai_tool_call_converter(tool_calls_raw)
        
        chunk_response = ChunkResponse(
            content=text_content or "",
            tool_calls=tool_call_deltas
        )
        
        events = handler.feed(chunk_response)
        
        print(f"[Chunk {chunk_num}] → {len(events)} events emitted")
    
    # Finalize
    final_events = handler.finalize()
    print(f"[Finalize] → {len(final_events)} events emitted")
    
    print()
    print("STEP 2: Handler Internal Processing")
    print("-" * 40)
    
    # Get invocations directly from handler (which uses internal adapter)
    invocations = handler.get_all_invocations()
    
    print(f"Handler internal adapter created {len(invocations)} ToolInvocations")
    
    print()
    print("STEP 3: Results")
    print("-" * 40)
    
    for inv in invocations:
        print(f"  {inv}")
    
    print()
    print("=" * 80)
    print("UNIFIED SIMULATION COMPLETE!")
    print("=" * 80)
    
    return invocations, all_emitted_events


def test_unified_simulation():
    """Test the unified architecture."""
    invocations, events = run_unified_simulation()
    
    # Verify we got exactly one tool invocation
    assert len(invocations) == 1, f"Expected 1 invocation, got {len(invocations)}"
    
    inv = invocations[0]
    assert inv.name == "write_file", f"Expected tool name 'write_file', got {inv.name}"
    assert inv.arguments == {"path": "hello.py", "content": "print('Hello World')"}, f"Unexpected arguments: {inv.arguments}"
    # ID logic might differ slightly in real impl if it generates new ID for new call
    # but in our sim we passed an ID 'call_abc123' at the start
    # Real handler respects provided ID if present on FIRST delta
    assert inv.id == "call_abc123", f"Expected id 'call_abc123', got {inv.id}"
    
    # Verify events include both text and tool call segments
    event_types = [e.segment_type for e in events if e.segment_type]
    assert SegmentType.TEXT in event_types, "Missing TEXT segment"
    assert SegmentType.TOOL_CALL in event_types, "Missing TOOL_CALL segment"
    
    print("\n✓ All assertions passed!")


def test_parallel_tool_calls_unified():
    """Test parallel tool calls with unified architecture."""
    print()
    print("=" * 80)
    print("PARALLEL TOOL CALLS - UNIFIED ARCHITECTURE")
    print("=" * 80)
    print()
    
    handler = ApiToolCallStreamingResponseHandler(segment_id_prefix="parallel_")
    
    # Simulate parallel tool calls
    chunks = [
        # Both start simultaneously
        ChunkResponse(content="", tool_calls=[
            ToolCallDelta(index=0, call_id="call_write", name="write_file"),
            ToolCallDelta(index=1, call_id="call_bash", name="run_bash"),
        ]),
        # Args for tool 0
        ChunkResponse(content="", tool_calls=[
            ToolCallDelta(index=0, arguments_delta='{"path": "hello.py", "content": "print()"}'),
        ]),
        # Args for tool 1
        ChunkResponse(content="", tool_calls=[
            ToolCallDelta(index=1, arguments_delta='{"command": "python hello.py"}'),
        ]),
    ]
    
    for chunk in chunks:
        handler.feed(chunk)
    
    handler.finalize()
    
    # Get invocations directly from handler
    invocations = handler.get_all_invocations()
    
    print(f"Tool invocations created by HANDLER: {len(invocations)}")
    for inv in invocations:
        print(f"  {inv}")
    
    assert len(invocations) == 2
    
    write_inv = next((i for i in invocations if i.name == "write_file"), None)
    bash_inv = next((i for i in invocations if i.name == "run_bash"), None)
    
    assert write_inv is not None
    assert bash_inv is not None
    assert write_inv.arguments == {"path": "hello.py", "content": "print()"}
    assert bash_inv.arguments == {"command": "python hello.py"}
    
    print("\n✓ Parallel tool calls test passed!")
    print("=" * 80)


if __name__ == "__main__":
    test_unified_simulation()
    test_parallel_tool_calls_unified()

