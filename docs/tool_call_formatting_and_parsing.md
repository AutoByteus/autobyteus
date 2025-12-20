# Tool Call Formatting and Parsing Design

Date: 2025-12-20
Status: Draft
Authors: Autobyteus Core Team

## Context

Autobyteus supports multiple LLM providers that emit and consume different tool call
formats (JSON variants for OpenAI-style models, XML for Anthropic). The system must:

- Generate correct, provider-aware tool manifests for prompts.
- Parse provider-specific tool calls from LLM responses into a unified internal model.
- Allow a configuration override to force XML formatting/parsing when desired.
- Keep the pipeline extensible without coupling core agent logic to any one provider.

This document describes the current implementation as reflected in the codebase.

## Goals

1. Provider-aware tool manifests that include schema + usage examples.
2. Provider-aware parsing that yields a uniform `ToolInvocation` model.
3. Configurable override (`use_xml_tool_format`) at agent and team levels.
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
      │  (injects {{tools}} into system prompt)
      ▼
LLM
      ▼
LLMCompleteResponseReceivedEventHandler
      │
      ▼
ProviderAwareToolUsageProcessor
      │  (ProviderAwareToolUsageParser + ToolUsageParserRegistry)
      ▼
Provider-specific parser (JSON/XML)
      │
      ▼
ToolInvocation list
      │
      ▼
PendingToolInvocationEvent -> tool execution -> ToolResultEventHandler
```

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
- XML override forces XML formatters even for JSON providers.

The manifest itself is composed by `ToolManifestProvider`:

- Builds schema + example for each tool.
- For XML, prepends general XML usage guidelines and array formatting guidance.
- For JSON, renders schema dictionaries and embeds examples as formatted strings.

The manifest is injected into the system prompt by
`ToolManifestInjectorProcessor` using a Jinja2-style placeholder `{{tools}}`.
If the prompt is tools-only, a default instruction prefix is added.

Key files:
- `autobyteus/agent/system_prompt_processor/tool_manifest_injector_processor.py`
- `autobyteus/tools/usage/providers/tool_manifest_provider.py`
- `autobyteus/tools/usage/registries/tool_formatting_registry.py`
- `autobyteus/tools/usage/formatters/*`

### 3) Provider-aware Parsing

Parsing is the inverse of formatting and is implemented in two layers:

1) `ProviderAwareToolUsageParser` selects a parser based on the agent’s
   provider and the XML override flag.
2) `ToolUsageParserRegistry` maps `LLMProvider` -> parser instance.

Provider parsers currently in use:

- OpenAI-style JSON (`OpenAiJsonToolUsageParser`) for OPENAI, MISTRAL,
  DEEPSEEK, GROK.
- Gemini JSON (`GeminiJsonToolUsageParser`).
- XML (`DefaultXmlToolUsageParser`) for ANTHROPIC and XML override.
- A default JSON parser (`DefaultJsonToolUsageParser`) as fallback.

JSON parsing uses a robust extractor that scans both inline JSON and
```json``` fenced blocks, keeping order. Each JSON parser supports multiple
response shapes to tolerate provider or prompt variations.

XML parsing scans for `<tool name="...">` blocks and delegates argument
parsing to a state-machine-based XML arguments parser. Arrays are modeled
as repeated `<item>` tags, consistent with the XML examples in the manifest.

Key files:
- `autobyteus/tools/usage/parsers/provider_aware_tool_usage_parser.py`
- `autobyteus/tools/usage/registries/tool_usage_parser_registry.py`
- `autobyteus/tools/usage/parsers/*`
- `autobyteus/tools/usage/parsers/_json_extractor.py`

### 4) LLM Response Processing and Tool Invocation

Tool parsing is wired into the agent loop via a mandatory
`ProviderAwareToolUsageProcessor`:

- Executed early in the LLM response processing chain.
- Converts parsed tool calls into `ToolInvocation` objects.
- Assigns session-unique IDs (deterministic base ID + counter suffix).
- Enqueues `PendingToolInvocationEvent` for each invocation.

If parsing fails with a `ToolUsageParseException`, the
`LLMCompleteResponseReceivedEventHandler` logs and notifies the frontend
without killing the rest of the pipeline.

Tool execution results are aggregated by `ToolResultEventHandler`.
For multi-tool turns, results are reordered to match the invocation
sequence before being sent back to the LLM.

Key files:
- `autobyteus/agent/llm_response_processor/provider_aware_tool_usage_processor.py`
- `autobyteus/agent/handlers/llm_complete_response_received_event_handler.py`
- `autobyteus/agent/tool_invocation.py`
- `autobyteus/agent/handlers/tool_result_event_handler.py`

### 5) Configuration and Overrides

- `AgentConfig.use_xml_tool_format` forces XML formatting + parsing.
- `AgentTeamConfig.use_xml_tool_format` overrides all agents when set.
- Defaults are provider-aware (JSON for most, XML for Anthropic).

Key files:
- `autobyteus/agent/context/agent_config.py`
- `autobyteus/agent_team/bootstrap_steps/agent_configuration_preparation_step.py`

## Design Patterns

- Strategy: Provider-specific formatters and parsers implement common interfaces.
- Registry + Singleton: Central mappings from provider -> formatter/parser.
- Template Method: Base formatter/parser classes define required interfaces.
- Adapter: Provider-specific formats are adapted into uniform `ToolInvocation`.
- Chain of Responsibility: LLM response processors run in ordered sequence.
- Factory: ToolRegistry constructs tool instances from ToolDefinition metadata.

## Extensibility Guidelines

To add a new provider format:

1. Implement a schema formatter + example formatter.
2. Implement a parser that yields `ToolInvocation` objects.
3. Register both in `ToolFormattingRegistry` and `ToolUsageParserRegistry`.
4. Ensure the provider enum is defined in `LLMProvider`.

To add a new tool:

1. Create a `ToolDefinition` (argument/config schemas + description).
2. Register it in the tool registry.
3. The new tool will automatically appear in the manifest and be parseable.

## Notes and Caveats

- JSON parsing is intentionally permissive to tolerate provider output variance.
- XML parsing treats unknown tags as literal text and only interprets
  `<tool>`, `<arguments>`, `<arg>`, and `<item>`.
- The XML override should be used carefully for providers with strict
  tool-call expectations, as it bypasses provider-native formats.

