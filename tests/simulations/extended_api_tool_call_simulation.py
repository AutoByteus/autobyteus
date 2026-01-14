import logging
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Callable
import uuid

# --- Imports from Codebase ---
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta
from autobyteus.llm.utils.response_types import ChunkResponse
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.agent.streaming.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from autobyteus.agent.streaming.parser.invocation_adapter import ToolInvocationAdapter
from autobyteus.llm.converters import convert_openai_tool_calls, convert_gemini_tool_calls, convert_anthropic_tool_call

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# MOCKS
# =============================================================================

# OpenAI Mocks (Existing)
@dataclass
class MockOpenAIFunction:
    name: Optional[str] = None
    arguments: Optional[str] = None

@dataclass
class MockOpenAIToolCall:
    index: int
    id: Optional[str] = None
    function: Optional[MockOpenAIFunction] = None

# Gemini Mocks
@dataclass
class MockGeminiFunctionCall:
    name: str
    args: Dict[str, Any]

@dataclass
class MockGeminiPart:
    function_call: Optional[MockGeminiFunctionCall] = None

# Anthropic Mocks
@dataclass
class MockAnthropicContentBlock:
    type: str
    id: Optional[str] = None
    name: Optional[str] = None

@dataclass
class MockAnthropicDelta:
    type: str # 'input_json_delta' or 'text_delta'
    partial_json: Optional[str] = None
    text: Optional[str] = None

@dataclass
class MockAnthropicEvent:
    type: str # 'content_block_start', 'content_block_delta'
    index: Optional[int] = None
    content_block: Optional[MockAnthropicContentBlock] = None
    delta: Optional[MockAnthropicDelta] = None


# =============================================================================
# SIMULATION DATA GENERATORS
# =============================================================================

def simulate_openai_stream():
    """Yields (MockOpenAIToolCall, text)"""
    yield (MockOpenAIToolCall(index=0, id="call_openai_1", function=MockOpenAIFunction(name="write_file")), "")
    yield (MockOpenAIToolCall(index=0, function=MockOpenAIFunction(arguments='{"path": "openai.py", ')), "")
    yield (MockOpenAIToolCall(index=0, function=MockOpenAIFunction(arguments='"content": "print(1)"}')), "")

def simulate_gemini_stream():
    """Yields MockGeminiPart (Simulates parts in candidate)"""
    # Gemini typically sends full function call in one go
    fc = MockGeminiFunctionCall(
        name="write_file",
        args={"path": "gemini.py", "content": "print(2)"}
    )
    yield MockGeminiPart(function_call=fc)

def simulate_anthropic_stream():
    """Yields MockAnthropicEvent"""
    # 1. Start tool use
    yield MockAnthropicEvent(
        type="content_block_start",
        index=0,
        content_block=MockAnthropicContentBlock(type="tool_use", id="call_anthropic_1", name="write_file")
    )
    # 2. Delta 1
    yield MockAnthropicEvent(
        type="content_block_delta",
        index=0,
        delta=MockAnthropicDelta(type="input_json_delta", partial_json='{"path": "anthropic.py", ')
    )
    # 3. Delta 2
    yield MockAnthropicEvent(
        type="content_block_delta",
        index=0,
        delta=MockAnthropicDelta(type="input_json_delta", partial_json='"content": "print(3)"}')
    )


# =============================================================================
# RUNNER
# =============================================================================

def run_simulation(provider: str, generator, converter_func):
    print(f"\n--- Simulating {provider} Flow ---")
    
    provider_lower = provider.lower()
    handler = ApiToolCallStreamingResponseHandler(segment_id_prefix=f"{provider_lower}_")
    
    events = []
    chunk_count = 0
    
    # Process stream
    for item in generator():
        chunk_count += 1
        
        # 1. Convert to ToolCallDelta
        # Different converters take different inputs
        # We wrap them to match signature if needed, but our mocks match converter expectations
        # OpenAI converter expects LIST of deltas
        
        tool_call_deltas = None
        if provider == "OpenAI":
            tool_call_deltas = converter_func([item[0]] if item[0].index is not None else [])
        elif provider == "Gemini":
            tool_call_deltas = converter_func(item)
        elif provider == "Anthropic":
            tool_call_deltas = converter_func(item)
            
        # 2. Feed to Handler
        chunk_response = ChunkResponse(
            content="",
            tool_calls=tool_call_deltas,
            is_complete=False
        )
        
        emitted = handler.feed(chunk_response)
        events.extend(emitted)
        print(f"[{provider} Chunk {chunk_count}] Emitted {len(emitted)} segment events")

    # Finalize
    final_events = handler.finalize()
    events.extend(final_events)
    print(f"[{provider} Finalize] Emitted {len(final_events)} segment events")
    
    # 3. Get Invocations
    invocations = handler.get_all_invocations()
    print(f"\n[{provider} Result] Created {len(invocations)} ToolInvocations:")
    for inv in invocations:
        print(f"  {inv}")
        
    return invocations


def test_converters():
    print("="*60)
    print("EXTENDED API TOOL CALL SIMULATION")
    print("="*60)
    
    # 1. OpenAI
    inv_openai = run_simulation("OpenAI", simulate_openai_stream, convert_openai_tool_calls)
    assert len(inv_openai) == 1
    assert inv_openai[0].name == "write_file"
    assert inv_openai[0].arguments == {"path": "openai.py", "content": "print(1)"}
    
    # 2. Gemini
    inv_gemini = run_simulation("Gemini", simulate_gemini_stream, convert_gemini_tool_calls)
    assert len(inv_gemini) == 1
    assert inv_gemini[0].name == "write_file"
    assert inv_gemini[0].arguments == {"path": "gemini.py", "content": "print(2)"}
    
    # 3. Anthropic
    inv_anthropic = run_simulation("Anthropic", simulate_anthropic_stream, convert_anthropic_tool_call)
    assert len(inv_anthropic) == 1
    assert inv_anthropic[0].name == "write_file"
    assert inv_anthropic[0].arguments == {"path": "anthropic.py", "content": "print(3)"}
    
    print("\n" + "="*60)
    print("ALL PROVIDERS VERIFIED SUCCESSFULLY!")
    print("="*60)

if __name__ == "__main__":
    test_converters()
