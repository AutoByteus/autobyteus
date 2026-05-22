# Investigation Notes

## Investigation Status

- Current Status: `Current`
- Scope Triage: `Medium`
- Triage Rationale: The change follows established image/audio patterns, but crosses multiple owned layers: public tool exports, multimedia model/client/provider registries, the shared HTTP client, response types, and focused validation. It is larger than a single local tool addition but does not require a new architecture.
- Investigation Goal: Determine the correct `autobyteus` implementation path for a video-generation tool backed by the sibling Autobyteus RPA LLM server video API.
- Primary Questions To Resolve:
  - How do existing image and speech tools expose model-backed multimedia generation?
  - Which layers own remote Autobyteus model discovery and execution?
  - What exact video API contract exists in the sibling server project?
  - Where should a new video tool be registered and exported?

## Source Log

| Date | Source Type | Exact Source / Query / Command | Why Consulted | Relevant Findings | Follow-Up Needed |
| --- | --- | --- | --- | --- | --- |
| 2026-05-22 | Doc | `README.md` | Confirm project setup and test command | Project uses Python 3.11 and `uv`; tests should run through `uv run python -m pytest`. | No |
| 2026-05-22 | Doc | `AGENTS.md` | Confirm repo-specific workflow expectations | Start with architecture docs, prefer TDD, use `uv run python -m pytest`, and stage explicit files only in git. | No |
| 2026-05-22 | Doc | `ARCHITECTURE.md`, `docs/agent_processor_and_engine_design.md`, `docs/tool_schema_and_configuration.md` | Confirm tool subsystem boundaries | Tools register as `ToolDefinition`s, schema comes from `ParameterSchema`, and tool execution runs through the standard registry/metaclass path. | Docs sync should assess whether multimedia docs need an update. |
| 2026-05-22 | Code | `autobyteus/tools/multimedia/image_tools.py` | Understand image tool pattern | `GenerateImageTool` and `EditImageTool` use env-configured model identifiers, dynamic `generation_config` schemas, shared per-agent image clients, `download_file_from_url`, and workspace-relative output paths. | Reuse pattern for video tool. |
| 2026-05-22 | Code | `autobyteus/tools/multimedia/audio_tools.py` | Understand speech tool pattern | `GenerateSpeechTool` uses `DEFAULT_SPEECH_GENERATION_MODEL`, dynamic model schema, direct audio client creation, output download, and cleanup. | Reuse simpler direct-client cleanup unless video needs shared state. |
| 2026-05-22 | Code | `autobyteus/multimedia/image/*`, `autobyteus/multimedia/audio/*` | Identify client/model/factory/provider pattern | Each modality has `Base*Client`, `*Model`, `*ClientFactory`, `Autobyteus*ModelProvider`, `api/autobyteus_*_client.py`, and package exports. | Add a parallel `video` package instead of mixing video into image/audio. |
| 2026-05-22 | Code | `autobyteus/clients/autobyteus_client.py` | Check remote client API surface | Existing methods support `/models/image`, `/models/audio`, `/generate-image`, `/generate-speech`, `/cleanup/image`, and `/cleanup/audio`; video methods are missing. `send_message` and `stream_message` already normalize video inputs for LLM chat. | Add video discovery/generation/cleanup methods. |
| 2026-05-22 | Code | `autobyteus/multimedia/utils/response_types.py`, `autobyteus/multimedia/utils/__init__.py` | Check response abstractions | There are `ImageGenerationResponse` and `SpeechGenerationResponse`, but no video response type. | Add `VideoGenerationResponse`. |
| 2026-05-22 | Code | `autobyteus/tools/__init__.py`, `autobyteus/tools/multimedia/__init__.py`, `autobyteus/tools/tool_meta.py`, `autobyteus/tools/registry/tool_registry.py` | Confirm public registration/export behavior | Concrete `BaseTool` subclasses auto-register at import time through `ToolMeta`; package imports expose multimedia tools. | Export `GenerateVideoTool` alongside image/audio tools. |
| 2026-05-22 | Command | `rg -n "generate_image|generate_speech|models/image|models/audio|cleanup/image|cleanup/audio|video" tests autobyteus -g '*.py'` | Find affected symbols and existing video support | Existing library supports video only for LLM user messages/media reading, not video generation tools or multimedia clients. | No |
| 2026-05-22 | Command | `rg -n "models/video|generate-video|generate_video|cleanup/video|video_urls" ../autobyteus_rpa_llm_workspace/... -g '*.py'` | Verify sibling server video contract | Server exposes `/models/video`, `/generate-video`, `/cleanup/video`, plus unit/E2E tests. | Use this contract directly. |
| 2026-05-22 | Code | `../autobyteus_rpa_llm_workspace/autobyteus_rpa_llm_server/autobyteus_rpa_llm_server/api/schemas.py` | Confirm video request/response schema | `GenerateVideoRequest` fields: `model_name`, `prompt`, optional `input_image_urls`, `input_audio_urls`, `input_video_urls`, optional `generation_config`, optional `session_id`; response field `video_urls`. | Match client method signature to these field names. |
| 2026-05-22 | Code | `../autobyteus_rpa_llm_workspace/autobyteus_rpa_llm_server/autobyteus_rpa_llm_server/api/endpoints.py` | Confirm endpoint paths and model response | `/models/video` returns `name`, `value`, `provider`, `config`, `parameter_schema`, and `description`; `/generate-video` returns absolute `video_urls`; `/cleanup/video` cleans session. | Provider should preserve description like image provider does. |
| 2026-05-22 | Code | `../autobyteus_rpa_llm_workspace/autobyteus_rpa_llm_server/autobyteus_rpa_llm_server/services/video_model_service.py` | Understand server-side state and input handling | Server materializes image/audio/video inputs, reuses clients by `session_id`, and saves returned videos as served media. | Library can pass local paths/URLs/data URIs; server handles materialization. |
| 2026-05-22 | Code | `../autobyteus_rpa_llm_workspace/autobyteus_rpa_llm/autobyteus_rpa_llm/video/rpa_video_client_factory.py` | Verify model name and schema | RPA model name is `gemini-omni-app-rpa`, value `gemini-omni-app`, provider `AUTOBYTEUS`, empty parameter schema, description says text plus optional image/audio/video inputs. | Use `gemini-omni-app-rpa` as the default video model. |

## Current Behavior / Codebase Findings

### Entrypoints And Boundaries

- Primary current tool entrypoints:
  - `GenerateImageTool` and `EditImageTool` in `autobyteus/tools/multimedia/image_tools.py`.
  - `GenerateSpeechTool` in `autobyteus/tools/multimedia/audio_tools.py`.
  - `ReadMediaFile` already accepts image/audio/video for LLM context, but it is a reader, not a generator.
- Execution boundaries:
  - Public tool classes own LLM-facing schemas, workspace output path resolution, and download/copy of the generated media.
  - Modality factories own model registry initialization and provider discovery.
  - `AutobyteusClient` owns HTTP transport to the RPA LLM server and media source normalization.
  - Remote `autobyteus_rpa_llm_server` owns browser/RPA execution and generated media serving.
- Owning subsystems / capability areas:
  - `autobyteus/tools/multimedia`: LLM-facing local tools.
  - `autobyteus/multimedia/<modality>`: modality-specific clients, models, factory/provider registration.
  - `autobyteus/clients`: shared HTTP client boundary.
  - `autobyteus/utils`: path and download helpers.
- Folder / file placement observations:
  - A new `autobyteus/multimedia/video/` package is the natural peer of `image/` and `audio/`.
  - A new `autobyteus/tools/multimedia/video_tools.py` should be a peer of `image_tools.py` and `audio_tools.py`.
  - Video should not be implemented inside image or audio files; that would mix modality ownership.

### Relevant Files / Symbols

| Path | Symbol / Area | Current Responsibility | Finding / Observation | Ownership / Placement Implication |
| --- | --- | --- | --- | --- |
| `autobyteus/tools/multimedia/image_tools.py` | `GenerateImageTool`, `EditImageTool` | LLM-facing image tools | Dynamic schema and output-saving pattern is directly reusable. | Video tool should mirror this, with video-specific input fields. |
| `autobyteus/tools/multimedia/audio_tools.py` | `GenerateSpeechTool` | LLM-facing speech tool | Simpler one-client lifecycle and dynamic schema pattern is reusable. | Video can follow audio for direct client management. |
| `autobyteus/multimedia/image/image_client_factory.py` | `ImageClientFactory` | Image model registry and remote discovery | Built-ins plus `AutobyteusImageModelProvider.discover_and_register()`. | Add `VideoClientFactory` with remote discovery; no built-in API video model is needed for this ticket. |
| `autobyteus/multimedia/audio/audio_client_factory.py` | `AudioClientFactory` | Audio model registry and remote discovery | Same provider/factory shape as image. | Use the same shape for video. |
| `autobyteus/multimedia/image/autobyteus_image_provider.py` | `AutobyteusImageModelProvider` | Discovers `/models/image` from configured hosts | Uses `AUTOBYTEUS_LLM_SERVER_HOSTS`, validates host URL, registers remote models. | Add a video provider using `/models/video`. |
| `autobyteus/multimedia/audio/autobyteus_audio_provider.py` | `AutobyteusAudioModelProvider` | Discovers `/models/audio` | Same remote discovery pattern. | Keep video provider consistent. |
| `autobyteus/multimedia/image/api/autobyteus_image_client.py` | `AutobyteusImageClient` | Remote image API adapter | Maintains `session_id`; calls `AutobyteusClient.generate_image`; converts to `ImageGenerationResponse`; cleans `/cleanup/image`. | Add equivalent video adapter. |
| `autobyteus/multimedia/audio/api/autobyteus_audio_client.py` | `AutobyteusAudioClient` | Remote speech API adapter | Maintains `session_id`; calls `generate_speech`; cleans `/cleanup/audio`. | Add equivalent video adapter. |
| `autobyteus/clients/autobyteus_client.py` | `AutobyteusClient` | Shared HTTP transport | Missing `/models/video`, `/generate-video`, and `/cleanup/video`; already has media normalization helpers. | Extend existing authoritative HTTP boundary. |
| `autobyteus/multimedia/utils/response_types.py` | Response dataclasses | Modality response containers | No video response dataclass exists. | Add `VideoGenerationResponse(video_urls: List[str])`. |
| `autobyteus/tools/__init__.py` | Public tool exports | Imports tool modules so metaclass registration happens | Does not import speech currently at top-level, but multimedia package exports it. Image tools are top-level exported. | Export video in multimedia and top-level tools for discoverability. |
| `tests/unit_tests/clients/test_autobyteus_client.py` | HTTP client tests | Verifies media source normalization for send/image methods | Good place for a `generate_video` normalization/payload test. | Add focused client unit test. |

### Runtime / Probe Findings

No live server probe was required in Stage 1. The sibling project was already validated in the previous ticket and its local code confirms the server contract. Stage 7 should include executable validation through mocks/unit tests and, if a running local server is available and credentials are configured, a lightweight remote contract smoke.

## External Code / Dependency Findings

- Upstream / sibling repo examined: `../autobyteus_rpa_llm_workspace`
- Relevant files:
  - `autobyteus_rpa_llm_server/autobyteus_rpa_llm_server/api/schemas.py`
  - `autobyteus_rpa_llm_server/autobyteus_rpa_llm_server/api/endpoints.py`
  - `autobyteus_rpa_llm_server/autobyteus_rpa_llm_server/services/video_model_service.py`
  - `autobyteus_rpa_llm/autobyteus_rpa_llm/video/rpa_video_client_factory.py`
  - `autobyteus_rpa_llm/autobyteus_rpa_llm/video/gemini_app_video_client.py`
- Relevant behavior:
  - Server model discovery endpoint is `GET /models/video`.
  - Generation endpoint is `POST /generate-video`.
  - Cleanup endpoint is `POST /cleanup/video`.
  - Video generation supports prompt plus optional image/audio/video inputs.
  - Server response is `{"video_urls": [...]}`.
  - The available model is currently `gemini-omni-app-rpa`.
- Confidence and freshness: High. The sibling project was just finalized/released in the current working session, and the local workspace contains the exact source code used for that release.

## Reproduction / Environment Setup

- Required services for live validation: an Autobyteus RPA LLM server with `AUTOBYTEUS_LLM_SERVER_HOSTS` pointing at it and `AUTOBYTEUS_API_KEY` configured.
- Required model configuration: `DEFAULT_VIDEO_GENERATION_MODEL` should default to `gemini-omni-app-rpa`; remote discovery creates the host-qualified identifier when hosts are configured, for example `gemini-omni-app-rpa@localhost:8000`.
- Local project test runner: `uv run python -m pytest ...`.
- No temporary code, scripts, or durable probes were created during Stage 1.

## External / Internet Findings

No internet research was used. Local code and sibling project source provided the needed API contract.

## Constraints

- Technical constraints:
  - Preserve the existing multimedia pattern: model metadata in `*Model`, registry in `*ClientFactory`, remote discovery in `Autobyteus*ModelProvider`, and execution in `api/autobyteus_*_client.py`.
  - Use `AutobyteusClient` as the single HTTP boundary; do not duplicate browser/RPA execution logic in `autobyteus`.
  - Do not introduce backward-compatibility or legacy fallback branches.
  - Dynamic `generation_config` schema should only appear when the selected model has a non-empty `parameter_schema`, matching image/audio tools.
- Environment constraints:
  - Live video generation is expensive/rate-limited and depends on Google login in the server container, so unit/contract tests should not require live video generation by default.
  - Tests must run through `uv run python -m pytest`.
- Third-party / API constraints:
  - The server currently exposes an empty parameter schema for `gemini-omni-app-rpa`; tool schema may not include `generation_config` unless future server model metadata adds parameters.

## Unknowns / Open Questions

- Unknown: Whether top-level `autobyteus.tools` should export `GenerateSpeechTool` too while adding video.
  - Why it matters: Avoid incidental API cleanup outside this ticket.
  - Planned follow-up: Keep source edits limited to video unless tests reveal a registration issue.
- Unknown: Whether the project wants live integration tests that hit the RPA server in CI.
  - Why it matters: Live video tests are slow and require browser login/API key.
  - Planned follow-up: Add env-gated integration coverage only if it can skip cleanly without credentials/server.

## Implications

### Requirements Implications

- Requirements should explicitly cover:
  - `generate_video` tool name and schema.
  - Prompt plus optional image/audio/video inputs.
  - Output video saved to a workspace-relative or absolute local path.
  - Remote Autobyteus server model discovery and execution.
  - Existing image/audio behavior remains unchanged.

### Design Implications

- The main data-flow spine should be:
  - `GenerateVideoTool -> VideoClientFactory/VideoModel -> AutobyteusVideoClient -> AutobyteusClient -> RPA LLM server /generate-video -> download_file_from_url`.
- Remote discovery spine should be:
  - `VideoClientFactory.ensure_initialized -> AutobyteusVideoModelProvider -> AutobyteusClient.get_available_video_models_sync -> VideoModel registration`.
- The authoritative boundary for remote HTTP calls is `AutobyteusClient`; video clients should not reach into `httpx` directly.

### Implementation / Placement Implications

- Add new files under `autobyteus/multimedia/video/`.
- Add `autobyteus/tools/multimedia/video_tools.py`.
- Modify shared exports and response types.
- Modify `autobyteus/clients/autobyteus_client.py` to add video methods.
- Add tests around client payload normalization, video model/registry/provider behavior, and tool schema/execute delegation.

## Re-Entry Additions

Append new dated evidence here when later stages reopen investigation.
