# API Tool Call File Streaming (write_file / patch_file)

Date: 2026-01-14  
Status: Draft  
Authors: Autobyteus Core Team

## Summary

When `AUTOBYTEUS_STREAM_PARSER=api_tool_call`, the current streaming handler emits only
`tool_call` segments and streams **raw JSON argument deltas**. This prevents the
frontend from receiving `write_file` / `patch_file` segment events and therefore
blocks file-content streaming.

This document proposes a targeted enhancement to `ApiToolCallStreamingResponseHandler`
that **recognizes file tools** and emits `write_file` / `patch_file` segments with
streamed content, while preserving existing behavior for all other tools.

No WebSocket protocol changes are required.

---

## Background

- The XML/JSON parser path can emit `write_file` / `patch_file` segments and stream
  content safely (including sentinel markers).
- In API tool call mode, tool calls arrive as incremental JSON deltas
  (e.g., OpenAI `tool_calls[].function.arguments` chunks).
- Today, `ApiToolCallStreamingResponseHandler` emits:
  - `SEGMENT_START` with `segment_type=tool_call`
  - `SEGMENT_CONTENT` containing raw JSON deltas
  - `SEGMENT_END` with pre-parsed arguments
- The frontend sees only `tool_call` segments and cannot stream file content.

---

## Goals

1. Emit `write_file` / `patch_file` **segment events** in API tool call mode.
2. Stream **file content** (`content`/`patch`) incrementally to the UI.
3. Preserve the **segment ID = tool invocation ID** guarantee.
4. Avoid duplicate tool invocations.
5. Do not change the external WebSocket protocol.

## Non-Goals

- General-purpose JSON streaming parser for all tools.
- Modifying provider SDK tool-calling payloads.
- Introducing new WebSocket message types.

---

## Design Overview

### High-Level Behavior

For tool calls with `tool_name` in `{write_file, patch_file}`:

- Emit `SEGMENT_START` with `segment_type=write_file` or `patch_file`.
- Stream **only the decoded content string** (`content` or `patch`) via
  `SEGMENT_CONTENT`.
- Emit `SEGMENT_END` when the tool call completes.
- Do **not** emit a `tool_call` segment for these tools (prevents duplicate
  ToolInvocation creation).

For all other tools:

- Keep the existing `tool_call` segment emission as-is.

### Why This Works

- `ToolInvocationAdapter` already supports `SegmentType.WRITE_FILE` and
  `SegmentType.PATCH_FILE` via `tool_syntax_registry.py`.
- It builds arguments from:
  - start/end metadata (path)
  - streamed content buffer
- Therefore, emitting file segments is enough to produce the correct tool
  invocation and tool execution flow.

---

## Incremental JSON String Extraction

Tool argument deltas are arbitrary JSON fragments. We only need to extract two
string fields:

- `path` (string)
- `content` (string) for `write_file` OR `patch` (string) for `patch_file`

### Minimal Streaming Parser (State Machine)

Maintain per-tool-call parsing state:

- `mode`: `scan_key` | `read_key` | `expect_colon` | `expect_value` | `read_value`
- `current_key`: accumulated key string
- `in_string`: bool
- `escape`: bool
- `value_target`: None | `path` | `content` | `patch`
- `value_buffer`: decoded stream for the target value

#### Behavior

1. **Scan for key strings** outside string context.
2. When a key ends (`"` closed), match against `path`, `content`, or `patch`.
3. Expect `:` then a string value (`"`).
4. While reading a target value string, **decode escapes** and emit only the
   **newly decoded suffix** as `SEGMENT_CONTENT` (for content/patch).
5. When the string closes, mark `path` or `content/patch` complete.

### Escapes

- Support standard JSON escapes: `\\`, `\"`, `\n`, `\t`, `\r`.
- Stream decoded content (e.g., `\n` -> newline).

### Sentinel Tags (Optional)

Sentinel markers (e.g., `__START_CONTENT__`) can still appear inside the decoded
JSON string. If present, they can be stripped during streaming, but they do **not**
remove the need for JSON decoding.

---

## Segment Emission Rules

### File Tools

- **Start**:
  - Emit `SEGMENT_START` immediately when the tool call is detected.
  - Metadata may be empty at start (path can arrive later).
- **Content**:
  - Stream only decoded content/patch text.
- **End**:
  - Emit `SEGMENT_END` with metadata containing `path` once it is known
    (adapter merges start+end metadata).

### Other Tools

- Leave behavior unchanged (`tool_call` segments).

---

## Avoiding Duplicate Tool Invocations

`ApiToolCallStreamingResponseHandler` pipes emitted segments into
`ToolInvocationAdapter`. Emitting **both** `tool_call` and `write_file` segments
for the same tool call would create duplicate invocations.

Therefore:

- For file tools, emit **only** file segments.
- For all other tools, emit only `tool_call` segments.

---

## Compatibility & Protocol Impact

- No protocol changes: `SEGMENT_*` types already support `write_file` and
  `patch_file`.
- Frontend will automatically render file-streamed content (same as XML path).
- Tool invocation IDs remain identical to segment IDs.

---

## Implementation Plan

### Code Changes

1. **Add a lightweight JSON string extractor** for targeted keys
   (`path`, `content`, `patch`).
2. **Add file content streamers** for write/patch file tools.
3. **Extend** `ApiToolCallStreamingResponseHandler` to:
   - Detect `write_file` / `patch_file` tool calls.
   - Use the file content streamers to emit
     `SegmentType.WRITE_FILE` / `SegmentType.PATCH_FILE`.

### Files

- `autobyteus/agent/streaming/handlers/api_tool_call_streaming_response_handler.py`
- `autobyteus/agent/streaming/api_tool_call/json_string_field_extractor.py`
- `autobyteus/agent/streaming/api_tool_call/file_content_streamer.py`
- Tests:
  - `tests/unit_tests/agent/streaming/api_tool_call/test_json_string_field_extractor.py`
  - `tests/unit_tests/agent/streaming/api_tool_call/test_file_content_streamer.py`
  - `tests/unit_tests/agent/streaming/handlers/test_api_tool_call_streaming_response_handler.py`

---

## Testing Plan

1. **write_file streaming**:
   - path + content in multiple chunks, verify:
     - `SEGMENT_START` type `write_file`
     - streamed decoded content
     - invocation arguments match full content
2. **patch_file streaming**:
   - similar to write_file, with `patch` arg
3. **Escapes**:
   - content includes `\n`, `\"`, `\\`
4. **Out-of-order keys**:
   - `content` appears before `path`
5. **Non-file tools unchanged**:
   - still emit `tool_call` segments
6. **No duplicate invocations**:
   - one invocation per call ID

---

## Open Questions

- Should we gate this behavior behind a config flag?
- Do we want to strip sentinel markers (`__START_CONTENT__` / `__END_CONTENT__`)
  if they appear inside decoded JSON content?
- Should we expose a lightweight `SEGMENT_METADATA_UPDATED` event to set `path`
  late, or rely on `SEGMENT_END` metadata only?
