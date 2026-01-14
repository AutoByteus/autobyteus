# Tool Call Formatting and Parsing Design

Date: 2025-12-20
Status: Draft
Authors: Autobyteus Core Team

## Context

Autobyteus supports multiple LLM providers that emit and consume different tool call
formats (JSON variants for OpenAI-style models, XML for Anthropic). The system must:

- Generate correct, provider-aware tool manifests for prompts.
- Parse provider-specific tool calls from LLM responses into a unified internal model.
- Allow a configuration override to force XML/JSON formatting/parsing when desired.
- Keep the pipeline extensible without coupling core agent logic to any one provider.

This document describes the current implementation as reflected in the codebase.

Related documentation:

- Streaming parser design and segment lifecycle: `docs/streaming_parser_design.md`

If you're new to the parsing flow, start with the streaming design doc above.
This document assumes the FSM emits segment events and the `ToolInvocationAdapter`
maps those segments into tool calls.

## Goals

1. Provider-aware tool manifests that include schema + usage examples.
2. Provider-aware parsing that yields a uniform `ToolInvocation` model.
3. Configurable override via `AUTOBYTEUS_STREAM_PARSER` when needed.
4. Resilience to mixed-content responses (tool calls embedded in free text).
5. Extensible registries for adding new providers or formats.

## Non-goals

- Designing new tool syntaxes beyond JSON/XML.
- Replacing the existing event-driven execution pipeline.
- Introducing new runtime registries for custom parsing strategies.

## High-level Flow

```
ToolDefinition registry
      │
      ▼
ToolManifestProvider
      │  (ToolFormattingRegistry selects schema + example formatters)
      ▼
ToolManifestInjectorProcessor
      │  (appends "Accessible Tools" section to system prompt)
      ▼
LLM
      ▼
LLMUserMessageReadyEventHandler
      │  (StreamingResponseHandler)
      ▼
StreamingParser + ToolInvocationAdapter
      │
      ▼
ToolInvocation list (per stream)
      │
      ▼
PendingToolInvocationEvent -> tool execution -> ToolResultEventHandler
```

## Formatter / Example / Parser Contract

Tool call formatting and parsing are tightly coupled. The formatter pair
(schema + example) defines the **shape** the LLM should emit, and the streaming
parser must recognize that exact shape.

```
ToolDefinition
  ├─ SchemaFormatter  -> tool schema
  └─ ExampleFormatter -> canonical example
             │
             ▼
      Tool manifest in prompt
             │
             ▼
      LLM output (matches example shape)
             │
             ▼
      StreamingParser + ToolInvocationAdapter
```

Key alignment rules:

- The **example formatter** establishes the surface syntax the parser expects.
- The **parser** must stay in lockstep with any example changes (XML tags or JSON envelopes).
- The **adapter** maps parsed segments to tool names/args (e.g., `<write_file>` -> `write_file`).

Concrete alignment points in code:

- XML examples (`DefaultXmlExampleFormatter`) emit `<tool>`/`<write_file>`/`<run_bash>` shapes that
  the XML tag parser recognizes (`XmlTagInitializationState`, `WriteFileParsingState`, etc.).
- JSON examples are provider-specific (OpenAI/Gemini/default) and must match the JSON
  parsing strategies in `autobyteus/agent/streaming/parser/json_parsing_strategies/`.
- The tool syntax registry (`autobyteus/agent/streaming/adapters/tool_syntax_registry.py`)
  defines how parsed segments become tool invocations.

## Core Components

### 1) ToolDefinition and Tool Registry

- `ToolDefinition` is the canonical source of tool metadata and schema providers.
- Argument and config schemas are generated lazily and cached.
- Description can be static or dynamically provided by the tool class.
- The registry (`ToolRegistry`) stores definitions and is used by manifest generation.

Why it matters:

- All formatting and parsing flows rely on `ToolDefinition` for stable names, schema,
  and descriptions.

Key files:

- `autobyteus/tools/registry/tool_definition.py`
- `autobyteus/tools/registry/tool_registry.py`

### 2) Tool Manifest Generation (Formatting)

Formatting is handled by a provider-aware registry of formatter pairs:

- `ToolFormattingRegistry` maps `LLMProvider` -> `ToolFormatterPair`.
- Each pair includes a schema formatter and an example formatter.
- Default fallback is JSON when a provider is unknown.
- Env override (`AUTOBYTEUS_STREAM_PARSER=xml|json`) forces a specific formatter.

The manifest itself is composed by `ToolManifestProvider`:

- Builds schema + example for each tool.
- For XML, prepends general XML usage guidelines and array formatting guidance.
- For JSON, renders schema dictionaries and embeds examples as formatted strings.

The manifest is injected into the system prompt by
`ToolManifestInjectorProcessor`, which appends an "Accessible Tools" section
directly at the end of the system prompt. No placeholder is required.

Key files:

- `autobyteus/agent/system_prompt_processor/tool_manifest_injector_processor.py`
- `autobyteus/tools/usage/providers/tool_manifest_provider.py`
- `autobyteus/tools/usage/registries/tool_formatting_registry.py`
- `autobyteus/tools/usage/formatters/*`

### 3) Streaming Parsing (FSM)

Parsing is performed during streaming by the FSM-based `StreamingParser`.

- `StreamingResponseHandler` feeds chunks and emits `SegmentEvent`s.
- `ToolInvocationAdapter` converts completed tool segments into `ToolInvocation`.
- Parser strategies are selected by `AUTOBYTEUS_STREAM_PARSER`:
  - `xml` (default): XML tag detection.
  - `json`: JSON tool detection.
  - `sentinel`: explicit sentinel markers.
  - `api_tool_call`: disables tool-tag parsing (provider-native tool calls only).

#### Provider-Aware JSON Parsing

JSON parsing is provider-aware to mirror the formatter registry:

- OpenAI-style formats (`tool_calls`, `tool`, `function`) use the OpenAI JSON parser.
- Gemini formats (`name` + `args`) use the Gemini JSON parser.
- Default JSON formats (`tool.function` + `parameters`) use the default parser.

The handler wires provider selection into `ParserConfig` by supplying:

- `json_tool_patterns`: signature patterns used by the JSON initialization state.
- `json_tool_parser`: the JSON parsing strategy to extract tool name + arguments.

This keeps JSON parsing aligned with provider-specific tool usage examples.

The parsing pipeline is representation-driven: any syntax that can be emitted
as a segment can become a tool call via the adapter. To add a new representation,
introduce a new segment type or strategy and register the mapping in
`autobyteus/agent/streaming/adapters/tool_syntax_registry.py`.

Key files:

- `autobyteus/agent/streaming/handlers/streaming_response_handler.py`
- `autobyteus/agent/streaming/parser/*`
- `autobyteus/agent/streaming/parser/json_parsing_strategies/*`

### 4) LLM Response Processing and Tool Invocation

Tool parsing is wired into the agent loop via the streaming handler:

- `LLMUserMessageReadyEventHandler` streams chunks through `StreamingResponseHandler`.
- Completed tool segments are converted into `ToolInvocation` objects.
- The handler enqueues `PendingToolInvocationEvent` entries once the stream is finalized.

**ID coupling guarantee:** the `ToolInvocation.id` for streamed tool calls is
**exactly the same** as the `segment_id` emitted by the streaming parser. This
means tool approval requests and UI segment rendering can be correlated without
any additional mapping.

Tool execution results are aggregated by `ToolResultEventHandler`.
For multi-tool turns, results are reordered to match the invocation
sequence before being sent back to the LLM.

Key files:

- `autobyteus/agent/handlers/llm_user_message_ready_event_handler.py`
- `autobyteus/agent/streaming/handlers/streaming_response_handler.py`
- `autobyteus/agent/tool_invocation.py`
- `autobyteus/agent/handlers/tool_result_event_handler.py`

### 5) Configuration and Overrides

- `AUTOBYTEUS_STREAM_PARSER` controls both the streaming parser strategy and
  the tool-call formatting override (`xml`, `json`, `sentinel`, `api_tool_call`).

- If `AUTOBYTEUS_STREAM_PARSER` is not set, the default is `api_tool_call`.
- When `AUTOBYTEUS_STREAM_PARSER` is set to `xml` or `json`, provider-aware
  parsing profiles apply (JSON for most providers, XML for Anthropic).

Key files:

- `autobyteus/agent/streaming/parser/parser_factory.py`
- `autobyteus/utils/tool_call_format.py`
- `autobyteus/agent/handlers/llm_user_message_ready_event_handler.py`

## Design Patterns

- Strategy: Provider-specific formatters implement common interfaces.
- Registry + Singleton: Central mappings from provider -> formatter pair.
- Adapter: Segment events are adapted into uniform `ToolInvocation`.
- Factory: ToolRegistry constructs tool instances from ToolDefinition metadata.

## Extensibility Guidelines

To add a new provider format:

1. Implement a schema formatter + example formatter.
2. Register the pair in `ToolFormattingRegistry`.
3. Ensure the provider enum is defined in `LLMProvider`.

To add a new tool:

1. Create a `ToolDefinition` (argument/config schemas + description).
2. Register it in the tool registry.
3. The new tool will automatically appear in the manifest and be parseable.

## Notes and Caveats

- The streaming parser only interprets configured tag formats; unknown tags are streamed as text.
- For provider-native tool calls, set `AUTOBYTEUS_STREAM_PARSER=api_tool_call`
  and rely on the provider stream.
