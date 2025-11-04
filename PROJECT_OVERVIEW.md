# AutoByteus Project Overview

This document outlines the current structure and execution model of the AutoByteus agentic framework so that client applications, SDK consumers, and the server project share a consistent architectural reference.

## High-Level Overview
- **Primary entry points**: `autobyteus/agent/factory/agent_factory.py` creates single agents, `autobyteus/agent_team/factory/agent_team_factory.py` assembles multi-agent teams, and `autobyteus/workflow/factory/workflow_factory.py` lifts teams into fully managed workflows.
- **Execution model**: Every agent, team, and workflow runs inside its own background thread hosting an `asyncio` event loop. Factories prepare contexts/states and spawn runtime workers (`agent/runtime/agent_runtime.py`, `agent_team/runtime/agent_team_runtime.py`, `workflow/runtime/workflow_runtime.py`).
- **Event & streaming plane**: Structured events are emitted through notifier/event-emitter pairs (`agent/events/notifiers.py`, `events/event_emitter.py`) and consumed via `AgentEventStream`, `AgentTeamEventStream`, and `WorkflowEventStream` for CLI/TUI surfaces.
- **Extension surface**: Pluggable processors, hooks, tools, and LLM providers live under `agent/*_processor`, `agent/hooks`, `tools/*`, and `llm/api`. Registries (`tools/registry`, `llm/extensions/extension_registry.py`) keep discovery dynamic.
- **Interfaces & transports**: Local CLIs (`cli/agent_cli.py`) and Textual TUIs (`cli/agent_team_tui/app.py`, `cli/workflow_tui/app.py`) provide interactive control. Remote execution is exposed through the RPC layer (`rpc/server_main.py`, `rpc/client/*`, `rpc/server/*`).

## Agent Runtime Lifecycle
1. **Configuration**: Users compose an `AgentConfig` with tools, LLM instances, workspace, and custom data (`agent/context/agent_config.py`).
2. **Factory assembly**: `AgentFactory.create_agent()` builds an `AgentRuntimeState`, wraps it in an `AgentContext`, registers it with `AgentContextRegistry`, prepares tool instances, and wires the default `EventHandlerRegistry`.
3. **Runtime bootstrap**: `AgentRuntime` spins up an `AgentWorker` thread. Inside the worker, `AgentBootstrapper` runs ordered bootstrap steps (queue init, system prompt setup, MCP pre-warming) before the agent accepts events.
4. **Event ingestion**: Incoming user messages, inter-agent messages, approvals, and system signals are funneled into typed queues (`agent/events/agent_input_event_queue_manager.py`). `WorkerEventDispatcher` routes them to specialized handlers.
5. **Phases & notifications**: `AgentPhaseManager` tracks operational phases (BOOTSTRAPPING → IDLE → RUNNING, etc.) and emits notifier events consumed by streamers and dashboards.
6. **Streaming & observability**: `AgentEventStream` coalesces notifier events into structured payloads (assistant chunks, tool logs, approvals, task notifications) for CLI/TUI layers and for higher-level workflow multiplexers.
7. **Shutdown**: `AgentShutdownOrchestrator` performs deterministic teardown (tool cleanup, workspace flush, context deregistration) before threads exit.

## Agent Teams & Workflows
- **Team definition**: `AgentTeamBuilder` builds nested trees of agents and sub-teams, producing `AgentTeamConfig` objects that embed notification modes, coordinator roles, and task policies (`agent_team/context/*.py`).
- **Team runtime**: `AgentTeamFactory.create_team()` mirrors the agent lifecycle—packing state, context, runtime, and a `TeamManager` that multiplexes member event streams. Teams expose `AgentTeamEventStream` to rebroadcast each agent’s output alongside team-level phase transitions.
- **Task notification modes**: `agent_team/task_notification/*` implements manual versus system-driven activation (`TaskNotificationMode`, `TaskActivator`, `SystemEventDrivenAgentTaskNotifier`). These modes integrate with task plans surfaced to coordinators and the TUIs.
- **Workflow orchestration**: `WorkflowFactory` layers an orchestration context on top of an agent team, creating an `AgenticWorkflow` facade that can post messages into targeted nodes and manage approvals. `WorkflowRuntime` hosts an `AgentEventMultiplexer` to rebroadcast all downstream agent/team events to the workflow-level TUI and RPC subscribers.

## Module Structure
```
autobyteus/
├── agent/              # Runtime, handlers, processors, hooks, context, streaming for single agents
├── agent_team/         # Builder, runtime, notification modes, streaming, and shutdown orchestration for teams
├── workflow/           # Workflow facades, factories, runtime, and event multiplexer for multi-team orchestration
├── tools/              # Base tool contract plus browser, file, process, search, multimedia, MCP, registry modules
├── llm/                # Provider adapters (OpenAI, Anthropic, Gemini, Mistral, etc.), token accounting, extensions
├── task_management/    # Task plan schemas, converters, and todo/task tools used by coordinators and dashboards
├── cli/                # Textual TUIs and interactive CLIs for agents, teams, and workflows
├── rpc/                # RPC server/client transports (stdio, SSE), protocol definitions, and configuration registries
├── multimedia/         # Audio/image APIs and utilities backing media-aware tools and agent capabilities
├── prompt/             # Prompt builders/templates for reusable instruction sets across agents and teams
├── events/             # Core event emitter/manager infrastructure shared across agent, team, and workflow layers
├── clients/            # High-level client wrappers (e.g., HTTPS + cert handling) for invoking remote AutoByteus servers
├── utils/              # Shared helpers (dynamic enums, file utilities, singleton base, schema helpers)
└── config.toml.template # Baseline runtime configuration example for local deployments
```

## CLI & UI Surfaces
- `cli/agent_cli.py` drives a REPL over a single agent using `AgentEventStream` for live updates and tool approvals.
- `cli/agent_team_tui/app.py` renders a Textual dashboard for hierarchical teams, combining team streams and per-agent logs.
- `cli/workflow_tui/app.py` builds the mission-control style UI that multiplexes entire workflows, providing throttled rendering, focus panes, and approval interactions.
- `cli/cli_display.py` and shared widgets coordinate terminal output, token accounting, and approval prompts.

## Remote Execution (RPC)
- `rpc/server_main.py` hosts agent/team/workflow control endpoints over stdio or Server-Sent Events. Method handlers live under `rpc/server/*` and translate RPC calls into factory/runtime operations.
- `rpc/client/*` implements pluggable transports (`stdio_client_connection.py`, `sse_client_connection.py`) so external SDKs can attach to a running AutoByteus runtime.
- `rpc/config/*` registers known agent servers and exposes strongly typed connection configs for the CLI and future SDKs.

## Tooling & Extension Points
- **Tool ecosystem**: `tools/base_tool.py` defines the contract; concrete tools live under `tools/browser`, `tools/process`, `tools/file`, `tools/multimedia`, `tools/mcp`, and `tools/search`. `tools/registry/tool_registry.py` resolves tools at runtime, while `tools/usage` records execution metadata.
- **Processors & hooks**: Input, response, and result processors (`agent/input_processor`, `agent/llm_response_processor`, `agent/tool_execution_result_processor`) plus lifecycle hooks (`agent/hooks`, `agent/phases`) allow deep customization without core changes.
- **LLM extensions**: `llm/extensions/token_usage_tracking_extension.py` demonstrates how to layer cross-cutting concerns onto provider calls; the registry pattern enables experimental features to be toggled per agent/team.
- **Workspace abstraction**: `agent/workspace` hosts file-system backed workspaces that tools and agents share, keeping artifacts scoped per agent/team.

## LLM & Prompt Management
- Provider adapters in `llm/api` wrap OpenAI-compatible, Anthropic, Gemini, Groq, Mistral, DeepSeek, NVIDIA, and local engines (Llama.cpp, LM Studio, Ollama, MLX). Each implements a unified request/response contract consumed by the runtime.
- `llm/utils` contains configuration builders, response typing, rate limiting, and token accounting utilities reused across agents and teams.
- `prompt/prompt_builder.py` and `prompt/prompt_template.py` standardize reusable prompt definitions so coordinators and specialists can share instruction scaffolding.

## Task & Conversation Utilities
- `task_management/tools` offers to-do and deliverable management utilities surfaced through system task notifications and TUI dashboards.
- `events/event_manager.py` coordinates the global event bus that the CLI/TUI layers subscribe to for phase changes, logs, and approvals.
- Conversation logging is persisted via rotating loggers (`logging_config.ini`, `logs/`) and optional artifacts captured in `agent/logs` files for post-run inspection.

## Testing Strategy & Structure
- Unit tests mirror the package layout, living under `tests/unit_tests/<package>/...`, enabling one-to-one navigation from source to tests. Integration tests follow the same pattern in `tests/integration_tests` but exercise real tool, multimedia, and provider interactions.
- `tests/utils` centralizes shared fixtures, test doubles, and helper builders (e.g., mock LLM responses, temporary workspaces).
- Async tests use `pytest-asyncio` with strict mode; long-running or provider-dependent cases are marked `@pytest.mark.slow` to allow selective execution.
- Common commands: `pytest` for the full suite, `pytest tests/unit_tests -k <keyword>` for targeted runs, and `pytest -m "not slow"` to skip slower integrations.

```
tests/
├── unit_tests/          # Mirrors agent, agent_team, workflow, tools, llm, task_management modules
├── integration_tests/   # Exercises provider adapters, multimedia codecs, and full agent/team pipelines
├── utils/               # Fixtures, fake providers, payload builders shared across suites
└── conftest.py          # Global pytest fixtures (event loop, temporary workspace, mock registries)
```

## Development Workflow Notes
- Install development extras with `pip install -r requirements-dev.txt` to obtain pytest, Textual, linting, and packaging tooling.
- Configure `.env` with provider keys before running examples or TUIs; `logging_config.ini` and `config.toml.template` demonstrate expected settings.
- Run packaged examples under `examples/` to exercise canonical workflows (e.g., `python autobyteus/examples/agent_team/event_driven/run_software_engineering_team.py --llm-model gpt-4o`).
- Build distributions via `python setup.py sdist bdist_wheel`; artifacts land in `dist/` and are consumed by `publish.sh` for release automation.
- For manual observability, tail `logs/` or the per-agent log files (e.g., `agent_logs.txt`) while driving the CLI/TUI.
