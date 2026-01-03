# Streaming Parser Design

Date: 2026-01-01  
Status: Implemented  
Authors: Autobyteus Core Team

## Overview

The streaming parser is a state-machine-based system that incrementally parses LLM response chunks in real-time. It handles structured content blocks (`<write_file>`, `<run_terminal_cmd>`, `<tool>`) while streaming safe content deltas to the frontend, preventing partial tags from being displayed.

## Goals

1. **Real-time streaming** – Parse LLM output character-by-character as chunks arrive.
2. **Safe content emission** – Never emit partial closing tags (e.g., `</wr` before `</write_file>`).
3. **Structured segment events** – Emit `SEGMENT_START`, `SEGMENT_CONTENT`, `SEGMENT_END` for each block.
4. **Extensibility** – Add new block types by creating new state classes.
5. **Provider-agnostic** – Works with any LLM provider's streaming output.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    StreamingResponseHandler                     │
│  (High-level API for feeding chunks and getting events)         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      StreamingParser                             │
│  (Orchestrates state machine, manages finalization)              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ParserContext                              │
│  - StreamScanner (character buffer)                              │
│  - EventEmitter (segment event queue)                            │
│  - Current state reference                                       │
└────────────────────────────────┬────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌───────────────┐    ┌───────────────────┐    ┌──────────────────┐
│   TextState   │    │ XmlTagInitState   │    │ JsonInitState    │
│ (default)     │◄──►│ (detects <tags>)  │◄──►│ (detects {json}) │
└───────────────┘    └─────────┬─────────┘    └──────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────────┐  ┌───────────────────────┐  ┌──────────────────┐
│WriteFileParsingState│  │RunTerminalCmdParsingState│  │XmlToolParsingState│
│(<write_file>...</write_file>)│  │(<run_terminal_cmd>...</run_terminal_cmd>)│  │(<tool>...</tool>)│
└──────────────────┘  └───────────────────────┘  └──────────────────┘
```

## Core Components

### StreamingResponseHandler

Entry point for the parser. Wraps `StreamingParser` and provides a simple API:

```python
from autobyteus.agent.streaming import StreamingResponseHandler

handler = StreamingResponseHandler()

# Feed chunks as they arrive
events = handler.feed("Hello <write_file path='/a.py'>")
events = handler.feed("print('hi')</write_file>")

# Finalize when stream ends
final_events = handler.finalize()
```

### ParserContext

Shared state container providing:

- **StreamScanner** – Character buffer with cursor position
- **EventEmitter** – Queues `SegmentEvent` objects
- **State management** – `transition_to()` for state changes
- **Configuration** – `parse_tool_calls`, `strategy_order` flags

### State Classes

All states extend `BaseState` and implement:

| Method       | Purpose                                                 |
| ------------ | ------------------------------------------------------- |
| `run()`      | Main parsing loop, consumes characters, emits events    |
| `finalize()` | Called when stream ends mid-parse, closes open segments |

#### TextState (Default)

Handles plain text. Watches for:

- `<` → transitions to `XmlTagInitializationState`
- `{` patterns → transitions to `JsonInitializationState`

#### XmlTagInitializationState

Accumulates characters after `<` to detect tag type:

- `<tool name="...">` → Dispatches to specific `Xml...ToolParsingState` based on tool name.
- `<write_file path="...">` → `CustomXmlTagWriteFileParsingState` (Legacy)
- `<run_terminal_cmd>` → `CustomXmlTagRunTerminalCmdParsingState` (Legacy)
- Unknown tags → emits as text, returns to `TextState`

#### Content Parsing States (Legacy Custom Tags)

The legacy states (`CustomXmlTagWriteFileParsingState`) use a robust buffer pattern (Holdback Pattern) to ensure safe emission, holding back characters to prevent partial closing tags from leaking.

#### Specialized XML Tool States (New Standard)

To ensure compatibility with the standard XML tool format (`<tool name="write_file">`) while mimicking the behavior of legacy custom tags, specialized states are used:

- **XmlWriteFileToolParsingState**:

  - **Deferred Start**: Buffers the initial stream until the `path` argument is found, ensuring `SEGMENT_START` always includes file path metadata.
  - **Pure Content Piping**: Extracts the inner text of `<arg name="content">` and streams _only_ that content, preventing XML markup from leaking to the frontend.
  - **Tag Swallowing**: Aggressively consumes and discards closing tags (`</arguments></tool>`) after content ends.

- **XmlRunTerminalCmdToolParsingState**:
  - Similar piping logic for the `command` argument.
  - Ensures `SEGMENT_START` is emitted, then streams only the command text.
  - Swallows trailing XML artifacts.

## Segment Events

The parser emits `SegmentEvent` objects with three lifecycle types:

| Event Type        | Payload                    | When Emitted                   |
| ----------------- | -------------------------- | ------------------------------ |
| `SEGMENT_START`   | `segment_type`, `metadata` | Opening tag detected           |
| `SEGMENT_CONTENT` | `delta` (text chunk)       | Content available to stream    |
| `SEGMENT_END`     | –                          | Closing tag found or finalized |

### Segment Types

```python
class SegmentType(str, Enum):
    TEXT = "text"
    TOOL_CALL = "tool_call"
    WRITE_FILE = "write_file"
    RUN_TERMINAL_CMD = "run_terminal_cmd"
    REASONING = "reasoning"
```

Tool syntax shorthands (e.g., `WRITE_FILE`, `RUN_TERMINAL_CMD`) map to concrete tools via the
tool syntax registry:

```
autobyteus/agent/streaming/parser/tool_syntax_registry.py
```

### Tool Syntax Mapping (SegmentType -> ToolInvocation)

The FSM only emits segment types; tool names are resolved later by the
`ToolInvocationAdapter` using the tool syntax registry.

| SegmentType      | Segment Syntax                             | Tool Name          | Argument Source                 |
| ---------------- | ------------------------------------------ | ------------------ | ------------------------------- |
| WRITE_FILE       | `<write_file path="...">`                  | `write_file`       | `path` from tag + segment body  |
| RUN_TERMINAL_CMD | `<run_terminal_cmd>...</run_terminal_cmd>` | `run_terminal_cmd` | `command` from body or metadata |

### Tool Invocation IDs (Important)

Tool invocations created from streamed tool segments **reuse the segment ID**.
This keeps a stable, 1:1 link between:

- `SegmentEvent.segment_id` in the streamed UI events
- `ToolInvocation.id` used in approval/execution

So when the frontend receives a tool approval request, the `invocation_id` is the
same value as the segment ID it already saw in the stream. This guarantees
reliable UI correlation without extra mapping.

## Safe Streaming (Holdback Pattern)

To prevent displaying partial closing tags in the UI, each content state holds back characters that could be part of the closing tag:

```
Buffer: "print('hi')</wr"
                    ^^^^ held back (chars = len("</write_file>") - 1)
Emitted: "print('hi')"
```

Once the full closing tag arrives:

```
Buffer: "print('hi')</write_file>"
                    ^^^^^^^^^^^^^  closing tag detected
Final emit: remaining content, then SEGMENT_END
```

## Integration with Event Handler

The `LLMUserMessageReadyEventHandler` integrates the parser:

```python
async def handle(self, event):
    streaming_handler = StreamingResponseHandler(on_part_event=emit_part_event)

    async for chunk in llm.stream_user_message(message):
        if chunk.content:
            streaming_handler.feed(chunk.content)

    streaming_handler.finalize()
```

## Parser Strategy Selection

The streaming system supports multiple parser strategies selected at runtime.

Environment variable:

- `AUTOBYTEUS_STREAM_PARSER`: `xml` (default), `json`, `native`, `sentinel`

When no override is set, the agent handler selects a parser strategy based on
provider (XML for Anthropic, JSON for most others). JSON parsing also uses
provider-aware signature patterns and parsing strategies to match tool
formatting examples.

Strategy notes:

- `xml`: state-machine parser tuned for XML tag detection.
- `json`: state-machine parser tuned for JSON tool detection.
- `native`: disables tool-tag parsing; tool calls are expected from the provider's native tool stream.
- `sentinel`: sentinel-based format using explicit start/end markers.
  - Sentinel format uses explicit start/end markers with a JSON header.

### Sentinel Format

Start marker:

```
[[SEG_START {"type":"write_file","path":"/a.py"}]]
```

End marker:

```
[[SEG_END]]
```

The `type` maps to `SegmentType`, and any other JSON fields are treated as metadata.

### Detection Strategies

Detection uses an ordered strategy list to decide which parser to invoke.

Default order:

```python
ParserConfig(strategy_order=["xml_tag"])
```

Each strategy reports the next candidate marker; the earliest match wins.

## Adding a New Block Type

1. Create a new state class in `parser/states/`:

```python
# my_block_parsing_state.py
class MyBlockParsingState(BaseState):
    CLOSING_TAG = "</myblock>"

    def __init__(self, context, opening_tag):
        # ... buffer setup

    def run(self):
        # ... parsing logic
```

2. Register detection in `XmlTagInitializationState`:

```python
if tag_name == "myblock":
    return StateFactory.my_block_parsing_state(self.context, opening_tag)
```

3. Add to `SegmentType` enum if needed.

## File Structure

```
autobyteus/agent/streaming/
├── __init__.py
├── streaming_response_handler.py    # High-level API
└── parser/
    ├── __init__.py
    ├── streaming_parser.py          # Orchestrator
    ├── parser_context.py            # Shared state + config
    ├── stream_scanner.py            # Character buffer
    ├── event_emitter.py             # Event queue
    ├── events.py                    # SegmentEvent, SegmentType
    ├── state_factory.py             # State creation
    ├── invocation_adapter.py        # Converts to ToolInvocation
    ├── json_parsing_strategies/     # Provider-aware JSON parsing
    └── states/
        ├── base_state.py
        ├── text_state.py
        ├── xml_tag_initialization_state.py
        ├── json_initialization_state.py
        ├── custom_xml_tag_write_file_parsing_state.py
        ├── custom_xml_tag_run_terminal_cmd_parsing_state.py
        ├── xml_tool_parsing_state.py
        ├── xml_write_file_tool_parsing_state.py
        ├── xml_run_terminal_cmd_tool_parsing_state.py
        └── json_tool_parsing_state.py
```

## Testing

Unit tests exist for each component:

```bash
# Run all streaming parser tests
uv run python -m pytest tests/unit_tests/agent/streaming/parser/ -v

# Run integration tests
uv run python -m pytest tests/integration_tests/agent/streaming/ -v
```

Test coverage includes:

- State transitions and detection
- Partial tag holdback behavior
- Multi-chunk streaming
- Finalization of incomplete blocks
- Mixed content scenarios
