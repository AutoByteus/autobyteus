# API Tool Call Streaming: Design & Implementation Document

Date: 2026-01-12
Status: Draft
Authors: Autobyteus Core Team

## 1. Problem Statement

Different LLM providers (OpenAI, Anthropic, Gemini) support **native tool calling** where tool
invocations are returned as structured data in the API response, separate from text content.
This is distinct from text-embedded tool calls (XML/JSON patterns in the response text).

The current streaming architecture was designed for text-based parsing and cannot handle
API-provided tool calls. We need to:

1. Extend the handler interface to receive rich `ChunkResponse` objects (not just strings).
2. Create a new handler (`ApiToolCallStreamingResponseHandler`) for API tool calls.
3. Add `ToolCallDelta` to `ChunkResponse` for normalized tool call streaming data.
4. Keep provider-specific conversion logic isolated in **Converters**.

---

## 2. Terminology

| Term                         | Definition                                                                                            |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Text-embedded tool calls** | Tool calls encoded as XML/JSON patterns within the LLM's text output. Requires parsing.               |
| **API tool calls**           | Tool calls returned as structured data by the LLM SDK, separate from text content. No parsing needed. |
| **ToolCallDelta**            | Provider-agnostic representation of a streaming tool call update.                                     |
| **ChunkResponse**            | Transport container for all streaming data from LLM (text, reasoning, tool calls).                    |

---

## 3. Architectural Overview

### 3.1. High-Level Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           LLM Provider SDK                                    │
│  (OpenAI: delta.tool_calls, Anthropic: input_json_delta, Gemini: etc.)       │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ SDK-specific format
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Provider-Specific Converter                                │
│  (OpenAIToolCallConverter, AnthropicToolCallConverter, etc.)                 │
│  Concern: Normalize SDK format → Common ToolCallDelta                         │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ List[ToolCallDelta]
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ChunkResponse                                       │
│  Fields: content, reasoning, tool_calls: List[ToolCallDelta], ...            │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   LLMUserMessageReadyEventHandler                             │
│  Selects handler based on AUTOBYTEUS_STREAM_PARSER:                          │
│    - "xml" / "json" / "sentinel" → ParsingStreamingResponseHandler           │
│    - "api_tool_call"             → ApiToolCallStreamingResponseHandler       │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ ChunkResponse (full object)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      StreamingResponseHandler                                 │
│  Base interface: feed(chunk: ChunkResponse) → List[SegmentEvent]             │
│                                                                              │
│  ┌───────────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │ ParsingStreamingResponseHandler │  │ ApiToolCallStreamingResponseHandler│ │
│  │ ┌───────────────────────────────┐  │  ┌──────────────────────────────┐ │ │
│  │ │ Internal ToolInvocationAdapter │  │  │ Internal ToolInvocationAdapter │ │ │
│  │ └───────────────────────────────┘  │  └──────────────────────────────┘ │ │
│  └───────────────────────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  │ get_all_invocations()
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     PendingToolInvocationEvent → Execution                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2. Unified ToolInvocation Creation

**Key Design Decision**: Both handlers have an **internal `ToolInvocationAdapter`** that processes
the events they emit. This provides:

1. **Single Responsibility**: Handlers emit events, adapters create invocations.
2. **Consistent Interface**: `get_all_invocations()` works the same for all handlers.
3. **Unified Logic**: Same adapter code handles both text-parsed and API tool calls.

**How the internal adapter works**:

```python
class ApiToolCallStreamingResponseHandler:
    def __init__(self, ...):
        self._adapter = ToolInvocationAdapter()  # Internal adapter
        self._all_invocations = []

    def _emit(self, event):
        self._all_events.append(event)
        if self._on_segment_event:
            self._on_segment_event(event)  # Notify UI

        # Process through internal adapter
        invocation = self._adapter.process_event(event)
        if invocation:
            self._all_invocations.append(invocation)

    def get_all_invocations(self):
        return self._all_invocations.copy()  # Returns adapter's results
```

**Event metadata contract**:

| Path          | SEGMENT_START           | SEGMENT_CONTENT              | SEGMENT_END                             |
| ------------- | ----------------------- | ---------------------------- | --------------------------------------- |
| Text Parsing  | `tool_name` in metadata | Raw XML/JSON text            | Adapter parses content buffer           |
| API Tool Call | `tool_name` in metadata | JSON args (for UI streaming) | Pre-parsed `arguments` dict in metadata |

---

## 4. Data Structures

### 4.1. `ToolCallDelta` (NEW)

**File**: `autobyteus/llm/utils/tool_call_delta.py`
**Concern**: Provider-agnostic representation of a single tool call update during streaming.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ToolCallDelta:
    """
    A normalized, provider-agnostic representation of a tool call update
    received during streaming.

    Attributes:
        index: Position in parallel tool calls (0-based). Used to track
               multiple concurrent tool calls.
        call_id: Unique ID for this tool call. Present only in the first
                 chunk for this index.
        name: Tool/function name. Present only in the first chunk for this index.
        arguments_delta: Partial JSON string of arguments. Accumulated across
                         multiple chunks to form complete arguments.
    """
    index: int
    call_id: Optional[str] = None
    name: Optional[str] = None
    arguments_delta: Optional[str] = None
```

**Relationships**:

- Created by: `OpenAIToolCallConverter`, `AnthropicToolCallConverter`, etc.
- Carried by: `ChunkResponse.tool_calls`
- Consumed by: `ApiToolCallStreamingResponseHandler`

### 4.2. `ChunkResponse` (MODIFIED)

**File**: `autobyteus/llm/utils/response_types.py`
**Concern**: Transport container for all chunk data from LLM stream.

```python
from dataclasses import dataclass, field
from typing import Optional, List
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta

@dataclass
class ChunkResponse:
    content: str  # Text content of the chunk
    reasoning: Optional[str] = None
    is_complete: bool = False
    usage: Optional[TokenUsage] = None
    image_urls: List[str] = field(default_factory=list)
    audio_urls: List[str] = field(default_factory=list)
    video_urls: List[str] = field(default_factory=list)
    # NEW FIELD:
    tool_calls: Optional[List[ToolCallDelta]] = None
```

---

## 5. Handler Interface Change

### 5.1. `StreamingResponseHandler` (MODIFIED)

**File**: `autobyteus/agent/streaming/handlers/streaming_response_handler.py`
**Change**: Accept `ChunkResponse` instead of `str`.

```python
from abc import ABC, abstractmethod
from typing import List
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import ChunkResponse
from .parser.events import SegmentEvent

class StreamingResponseHandler(ABC):
    """
    Abstract base class for handling streaming LLM responses.

    Handlers receive the full ChunkResponse and decide which fields to use:
    - Text parsers use chunk.content
    - API tool call handlers use chunk.tool_calls
    """

    @abstractmethod
    def feed(self, chunk: ChunkResponse) -> List[SegmentEvent]:
        """
        Process a chunk of LLM response.

        Args:
            chunk: The full ChunkResponse containing text, tool calls, etc.

        Returns:
            List of SegmentEvents emitted while processing this chunk.
        """
        pass

    @abstractmethod
    def finalize(self) -> List[SegmentEvent]:
        """Finalize streaming and emit any remaining segments."""
        pass

    @abstractmethod
    def get_all_invocations(self) -> List[ToolInvocation]:
        """Get all ToolInvocations created during streaming."""
        pass

    @abstractmethod
    def get_all_events(self) -> List[SegmentEvent]:
        """Get all SegmentEvents emitted during streaming."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the handler for reuse."""
        pass
```

### 5.2. `ParsingStreamingResponseHandler` (MODIFIED)

**Minimal change**: Extract text content from `ChunkResponse`.

```python
class ParsingStreamingResponseHandler(StreamingResponseHandler):
    def feed(self, chunk: ChunkResponse) -> List[SegmentEvent]:
        if self._is_finalized:
            raise RuntimeError("Handler has been finalized.")

        # Use text content for parsing (ignore tool_calls - not our concern)
        if not chunk.content:
            return []

        events = self._parser.feed(chunk.content)
        self._process_events(events)
        return events
```

### 5.3. `PassThroughStreamingResponseHandler` (MODIFIED)

**Minimal change**: Extract text content from `ChunkResponse`.

```python
class PassThroughStreamingResponseHandler(StreamingResponseHandler):
    def feed(self, chunk: ChunkResponse) -> List[SegmentEvent]:
        if not chunk.content:
            return []

        # Existing pass-through logic using chunk.content
        ...
```

---

## 6. New Handler: `ApiToolCallStreamingResponseHandler`

**File**: `autobyteus/agent/streaming/handlers/api_tool_call_streaming_response_handler.py`
**Concern**: Emit `SegmentEvent`s for API-provided tool calls. Does NOT create `ToolInvocation`s directly.

**Key Design**: This handler follows the single responsibility principle:

- Handler's job: Emit `SegmentEvent`s with structured data
- Adapter's job: Create `ToolInvocation`s from events

**SEGMENT_END Metadata Contract**: For API tool calls, the handler passes pre-parsed
arguments in the `SEGMENT_END` event's `metadata.arguments` field. The adapter uses
this instead of parsing the content buffer.

```python
import json
import uuid
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable

from .streaming_response_handler import StreamingResponseHandler
from .parser.events import SegmentEvent, SegmentType
from autobyteus.llm.utils.response_types import ChunkResponse
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)


@dataclass
class ToolCallState:
    """Tracks the state of an in-progress tool call."""
    segment_id: str
    name: str
    accumulated_args: str = ""


class ApiToolCallStreamingResponseHandler(StreamingResponseHandler):
    """
    Handler for API-provided tool calls (OpenAI, Anthropic, Gemini native tool calling).

    Responsibilities:
    1. Emit TEXT segments for text content
    2. Emit TOOL_CALL segments for SDK-provided tool calls
    3. Accumulate arguments and pass them via SEGMENT_END metadata

    Does NOT create ToolInvocations - that's the adapter's job.
    """

    def __init__(
        self,
        on_segment_event: Optional[Callable[[SegmentEvent], None]] = None,
        segment_id_prefix: str = "",
    ):
        self._on_segment_event = on_segment_event
        self._segment_id_prefix = segment_id_prefix

        # State tracking
        self._text_segment_id: Optional[str] = None
        self._active_tools: Dict[int, ToolCallState] = {}  # index -> state
        self._all_events: List[SegmentEvent] = []
        self._is_finalized = False

    def _generate_id(self) -> str:
        return f"{self._segment_id_prefix}{uuid.uuid4().hex}"

    def _emit(self, event: SegmentEvent) -> None:
        self._all_events.append(event)
        if self._on_segment_event:
            try:
                self._on_segment_event(event)
            except Exception as e:
                logger.error(f"Error in on_segment_event callback: {e}")

    def feed(self, chunk: ChunkResponse) -> List[SegmentEvent]:
        if self._is_finalized:
            raise RuntimeError("Handler has been finalized.")

        events = []

        # 1. Handle text content → TEXT segment
        if chunk.content:
            if self._text_segment_id is None:
                self._text_segment_id = self._generate_id()
                start_event = SegmentEvent.start(
                    segment_id=self._text_segment_id,
                    segment_type=SegmentType.TEXT
                )
                self._emit(start_event)
                events.append(start_event)

            content_event = SegmentEvent.content(
                segment_id=self._text_segment_id,
                delta=chunk.content
            )
            self._emit(content_event)
            events.append(content_event)

        # 2. Handle tool calls from SDK
        if chunk.tool_calls:
            for delta in chunk.tool_calls:
                if delta.index not in self._active_tools:
                    # New tool call - emit SEGMENT_START
                    seg_id = delta.call_id or self._generate_id()
                    self._active_tools[delta.index] = ToolCallState(
                        segment_id=seg_id,
                        name=delta.name or "",
                        accumulated_args=""
                    )

                    start_event = SegmentEvent.start(
                        segment_id=seg_id,
                        segment_type=SegmentType.TOOL_CALL,
                        tool_name=delta.name
                    )
                    self._emit(start_event)
                    events.append(start_event)

                # Accumulate arguments and emit content delta (for UI streaming)
                if delta.arguments_delta:
                    state = self._active_tools[delta.index]
                    state.accumulated_args += delta.arguments_delta

                    content_event = SegmentEvent.content(
                        segment_id=state.segment_id,
                        delta=delta.arguments_delta
                    )
                    self._emit(content_event)
                    events.append(content_event)

                # Update name if provided later
                if delta.name and not self._active_tools[delta.index].name:
                    self._active_tools[delta.index].name = delta.name

        return events

    def finalize(self) -> List[SegmentEvent]:
        if self._is_finalized:
            return []

        self._is_finalized = True
        events = []

        # Close text segment
        if self._text_segment_id:
            end_event = SegmentEvent.end(segment_id=self._text_segment_id)
            self._emit(end_event)
            events.append(end_event)

        # Close tool segments with pre-parsed arguments in metadata
        for state in self._active_tools.values():
            # Parse accumulated JSON arguments
            try:
                parsed_args = json.loads(state.accumulated_args) if state.accumulated_args else {}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool arguments for {state.name}: {e}")
                parsed_args = {}

            # Emit SEGMENT_END with arguments in metadata
            # The ToolInvocationAdapter will use this instead of parsing content
            end_event = SegmentEvent(
                event_type=SegmentEventType.END,
                segment_id=state.segment_id,
                payload={
                    "metadata": {
                        "tool_name": state.name,
                        "arguments": parsed_args,  # Pre-parsed for adapter
                    }
                }
            )
            self._emit(end_event)
            events.append(end_event)

        return events

    def get_all_events(self) -> List[SegmentEvent]:
        return self._all_events.copy()

    def get_all_invocations(self) -> List[ToolInvocation]:
        # This handler doesn't create invocations - the adapter does
        # Return empty list; invocations come from adapter processing events
        return []

    def reset(self) -> None:
        self._text_segment_id = None
        self._active_tools.clear()
        self._all_events.clear()
        self._is_finalized = False


# Need to import SegmentEventType for the END event with metadata
from .parser.events import SegmentEventType
```

---

## 6b. `ToolInvocationAdapter` Enhancement

**File**: `autobyteus/agent/streaming/adapters/invocation_adapter.py`
**Change**: Handle pre-parsed arguments from SEGMENT_END metadata (for API tool calls).

The adapter already checks `metadata.get("arguments")` - this is the hook we use:

```python
# In _handle_end method, existing logic already handles this:
if start_metadata.get("arguments"):
    arguments = start_metadata["arguments"]
elif metadata.get("arguments"):  # ← API tool calls provide this
    arguments = metadata["arguments"]
```

**No code change required** - the existing adapter logic already supports pre-parsed
arguments via metadata. The API tool call handler just needs to provide them.

---

## 7. Provider-Specific Converters

### 7.1. `OpenAIToolCallConverter`

**File**: `autobyteus/llm/converters/openai_tool_call_converter.py`
**Concern**: Convert OpenAI SDK tool call deltas to `ToolCallDelta`.

```python
from typing import List, Optional
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta


def convert(delta_tool_calls: Optional[List[ChoiceDeltaToolCall]]) -> Optional[List[ToolCallDelta]]:
    """
    Convert OpenAI SDK tool call deltas to normalized ToolCallDelta objects.

    Args:
        delta_tool_calls: List of ChoiceDeltaToolCall from OpenAI SDK, or None.

    Returns:
        List of normalized ToolCallDelta objects, or None if input is None/empty.
    """
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
```

### 7.2. Future Converters

- `AnthropicToolCallConverter`: Convert Anthropic's `content_block_delta` with `input_json_delta`
- `GeminiToolCallConverter`: Convert Gemini's `functionCall` responses

---

## 8. LLM Layer Integration

### 8.1. `OpenAICompatibleLLM._stream_user_message_to_llm` (MODIFIED)

```python
async def _stream_user_message_to_llm(
    self, user_message: LLMUserMessage, **kwargs
) -> AsyncGenerator[ChunkResponse, None]:
    # ... existing setup ...

    for chunk in stream:
        delta = chunk.choices[0].delta

        # Handle reasoning (existing logic)
        reasoning_chunk = None
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            reasoning_chunk = delta.reasoning_content

        # NEW: Convert tool calls
        tool_call_deltas = None
        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            from autobyteus.llm.converters.openai_tool_call_converter import convert
            tool_call_deltas = convert(delta.tool_calls)

        # Handle text content
        main_token = delta.content

        yield ChunkResponse(
            content=main_token or "",
            reasoning=reasoning_chunk,
            tool_calls=tool_call_deltas,  # NEW
        )
```

---

## 9. Handler Orchestration

### 9.1. `LLMUserMessageReadyEventHandler` (MODIFIED)

**Key changes**:

1. Pass full `ChunkResponse` to handler (not just `chunk.content`)
2. Select handler based on `AUTOBYTEUS_STREAM_PARSER`
3. Use `api_tool_call` for SDK tool calls

```python
# Determine handler type
format_override = resolve_tool_call_format()

if format_override == "api_tool_call":
    # Use API tool call handler - no parsing needed
    streaming_handler = ApiToolCallStreamingResponseHandler(
        on_segment_event=emit_segment_event,
        segment_id_prefix=segment_id_prefix,
    )
elif parse_tool_calls:
    # Use parsing handler for XML/JSON/Sentinel
    streaming_handler = ParsingStreamingResponseHandler(
        on_segment_event=emit_segment_event,
        config=parser_config,
        parser_name=format_override if format_override in {"xml", "json", "sentinel"} else "xml",
    )
else:
    # No tools - pass through
    streaming_handler = PassThroughStreamingResponseHandler(
        on_segment_event=emit_segment_event,
        segment_id_prefix=segment_id_prefix,
    )

# Stream processing loop
async for chunk_response in context.state.llm_instance.stream_user_message(llm_user_message):
    # ... aggregation logic ...

    # Feed full ChunkResponse to handler (not just content!)
    streaming_handler.feed(chunk_response)
```

---

## 10. Configuration

### 10.1. Environment Variable

`AUTOBYTEUS_STREAM_PARSER` values:

- `xml`: Parse XML tags in text
- `json`: Parse JSON in text
- `sentinel`: Parse sentinel-delimited tool calls in text
- `api_tool_call`: Use SDK-provided tool calls (no text parsing)

### 10.2. Agent Config

```python
@dataclass
class AgentConfig:
    # ...
    # Tool call format is controlled by AUTOBYTEUS_STREAM_PARSER (env var).
```

---

## 11. File Summary & Concerns

| File                                                          | Concern                                      | Status   |
| ------------------------------------------------------------- | -------------------------------------------- | -------- |
| `llm/utils/tool_call_delta.py`                                | Common data structure for tool call updates  | **NEW**  |
| `llm/utils/response_types.py`                                 | Add `tool_calls` field to `ChunkResponse`    | MODIFIED |
| `llm/converters/openai_tool_call_converter.py`                | Normalize OpenAI SDK format                  | **NEW**  |
| `llm/api/openai_compatible_llm.py`                            | Convert tool calls, include in ChunkResponse | MODIFIED |
| `agent/streaming/handlers/streaming_response_handler.py`               | Change `feed(str)` to `feed(ChunkResponse)`  | MODIFIED |
| `agent/streaming/handlers/parsing_streaming_response_handler.py`       | Use `chunk.content`                          | MODIFIED |
| `agent/streaming/handlers/pass_through_streaming_response_handler.py`  | Use `chunk.content`                          | MODIFIED |
| `agent/streaming/handlers/api_tool_call_streaming_response_handler.py` | New handler for SDK tool calls               | **NEW**  |
| `agent/handlers/llm_user_message_ready_event_handler.py`      | Handler selection, pass full ChunkResponse   | MODIFIED |
| `utils/tool_call_format.py`                                   | Remove legacy "native" alias                 | MODIFIED |

---

## 12. Migration Notes

### Breaking Changes

1. `StreamingResponseHandler.feed()` signature changed from `str` to `ChunkResponse`
2. Legacy environment variable value `native` removed; use `api_tool_call`

### Backward Compatibility

- Existing text-based tool parsing (XML/JSON/Sentinel) continues to work unchanged
- Only the interface changes; internal behavior of text parsers is preserved

---

## 13. Tool Schema Passing for API Tool Calls

> [!IMPORTANT]
> For API tool calls to work, tool schemas MUST be passed to the LLM API.
> Without this, the LLM doesn't know what tools are available.

### 13.1. Text-Embedded vs API Tool Calls

| Approach                 | How LLM learns about tools                    | How LLM calls tools                             |
| ------------------------ | --------------------------------------------- | ----------------------------------------------- |
| Text-embedded (XML/JSON) | Tool docs injected into system prompt as text | LLM outputs text patterns we parse              |
| API tool calls           | Tool schemas passed via API `tools` parameter | LLM returns structured `tool_calls` in response |

### 13.2. Existing Infrastructure

We already have formatters that convert tool definitions to API schemas:

```python
# autobyteus/tools/usage/formatters/openai_json_schema_formatter.py
class OpenAiJsonSchemaFormatter(BaseSchemaFormatter):
    def provide(self, tool_definition: 'ToolDefinition') -> Dict:
        return {
            "type": "function",
            "function": {
                "name": tool_definition.name,
                "description": tool_definition.description,
                "parameters": tool_definition.argument_schema.to_json_schema_dict(),
            },
        }
```

Similar formatters exist for:

- `AnthropicJsonSchemaFormatter`
- `GeminiJsonSchemaFormatter`

### 13.3. Design: Tool Schema Passing

**Option A: Pass via `LLMUserMessageReadyEventHandler` (Recommended)**

The handler already has access to tool definitions. When `api_tool_call` mode is selected:

1. Format tool definitions to API schema
2. Pass as `tools` kwarg to LLM stream

```python
# In LLMUserMessageReadyEventHandler.handle()
if format_override == "api_tool_call":
    # Get tool definitions from context
    tool_definitions = [
        default_tool_registry.get_tool_definition(name)
        for name in context.state.tool_names
    ]

    # Format for API
    formatter = OpenAiJsonSchemaFormatter()
    tools_schema = [formatter.provide(td) for td in tool_definitions if td]

    # Pass to LLM stream
    async for chunk in context.state.llm_instance.stream_user_message(
        llm_user_message,
        tools=tools_schema  # ← NEW: pass tools
    ):
        ...
```

**LLM layer change** in `_stream_user_message_to_llm`:

```python
async def _stream_user_message_to_llm(
    self, user_message: LLMUserMessage, **kwargs
) -> AsyncGenerator[ChunkResponse, None]:
    # ...
    params = {
        "model": self.model.value,
        "messages": formatted_messages,
        "stream": True,
    }

    # Include tools if provided
    if kwargs.get("tools"):
        params["tools"] = kwargs["tools"]

    stream = self.client.chat.completions.create(**params)
    # ...
```

### 13.4. File Changes for Tool Schema Passing

| File                                                     | Change                            |
| -------------------------------------------------------- | --------------------------------- |
| `agent/handlers/llm_user_message_ready_event_handler.py` | Format tool schemas, pass to LLM  |
| `llm/api/openai_compatible_llm.py`                       | Accept `tools` kwarg, pass to API |
| (similar for other LLM providers)                        | Accept `tools` kwarg              |

---

## 14. Future Considerations

1. **Provider Detection**: Auto-detect when to use `api_tool_call` based on provider capabilities
   instead of requiring explicit configuration.

2. **Hybrid Mode**: Some responses may contain both text-embedded and API tool calls.
   Current design handles this by treating them as separate concerns.

3. **Tool Choice**: Support `tool_choice` parameter for forcing specific tool usage.
