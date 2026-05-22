# Requirements

## Status

Refined

## Goal / Problem Statement

Add video-generation tool support to the `autobyteus` project so agents can call a first-class `generate_video` tool. The tool must follow the existing image and speech/audio multimedia architecture and delegate execution to the Autobyteus RPA LLM server video API rather than implementing browser automation in this library.

## Scope Classification

- Classification: `Medium`
- Rationale: The behavior follows established image/audio patterns, but it requires coordinated changes across public tool exports, multimedia model/client/provider registration, the shared HTTP client, response types, and tests.

## In-Scope Use Cases

| Use Case ID | Use Case | Primary Actor | Expected Outcome |
| --- | --- | --- | --- |
| UC-001 | Generate a video from a text prompt. | Agent / LLM tool caller | A video is generated remotely and saved to the requested local output path. |
| UC-002 | Generate a video from a prompt plus image references. | Agent / LLM tool caller | The tool passes image references to the video backend and saves the generated video. |
| UC-003 | Generate a video from a prompt plus audio references. | Agent / LLM tool caller | The tool passes audio references to the video backend and saves the generated video. |
| UC-004 | Generate a video from a prompt plus video references. | Agent / LLM tool caller | The tool passes video references to the video backend and saves the generated video. |
| UC-005 | Discover remote video models from configured Autobyteus server hosts. | Application / tool schema provider | Configured remote video models become available through the video model registry. |
| UC-006 | Keep existing image and speech/audio generation unchanged. | Existing users | Current image and audio APIs/tools continue to import, register, and execute as before. |

## Requirements

| Requirement ID | Requirement | Use Case IDs |
| --- | --- | --- |
| R-001 | Provide a concrete multimedia tool named `generate_video` with `ToolCategory.MULTIMEDIA`. | UC-001, UC-002, UC-003, UC-004 |
| R-002 | The tool must accept a required `prompt`, required `output_file_path`, and optional comma-separated `input_images`, `input_audios`, and `input_videos` arguments. | UC-001, UC-002, UC-003, UC-004 |
| R-003 | The tool must use a configured video model from `DEFAULT_VIDEO_GENERATION_MODEL`, falling back to `gemini-omni-app-rpa` when unset. Because remote Autobyteus model identifiers can be host-qualified, an unqualified model name must resolve to the unique discovered model with that name; ambiguous multi-host matches must raise a clear configuration error. | UC-001, UC-005 |
| R-004 | The tool schema must append a model-specific `generation_config` object only when the configured video model exposes a non-empty `parameter_schema`. | UC-001, UC-005 |
| R-005 | Video generation must delegate through a video multimedia client/factory/provider path that mirrors image/audio and ultimately calls the Autobyteus RPA LLM server `/generate-video` endpoint. | UC-001, UC-002, UC-003, UC-004, UC-005 |
| R-006 | The shared `AutobyteusClient` must expose video model discovery, video generation, and video session cleanup methods using the sibling server contract. | UC-001, UC-005 |
| R-007 | Remote video model discovery must use `AUTOBYTEUS_LLM_SERVER_HOSTS`, validate host URLs, call `/models/video`, and register valid returned models. | UC-005 |
| R-008 | Generated video output must be persisted with the existing `download_file_from_url` and `resolve_safe_path` behavior used by image/audio tools. | UC-001, UC-002, UC-003, UC-004 |
| R-009 | Existing image/audio public behavior and model discovery must not be changed except for shared exports required to add video. | UC-006 |
| R-010 | Do not add backward-compatibility shims, legacy aliases, or duplicate browser/RPA logic in `autobyteus`. | UC-001, UC-005, UC-006 |

## Acceptance Criteria

| Acceptance Criteria ID | Acceptance Criteria | Requirement IDs | Validation Intent |
| --- | --- | --- | --- |
| AC-001 | Importing `autobyteus.tools.multimedia` exposes `GenerateVideoTool`, and importing `autobyteus.tools` exposes `GenerateVideoTool` without breaking existing image/audio exports. | R-001, R-009 | Unit/import test. |
| AC-002 | The `generate_video` tool definition is registered through the existing `BaseTool` metaclass/registry path when the video tool module is imported. | R-001 | Unit/registry test. |
| AC-003 | `GenerateVideoTool.get_argument_schema()` contains `prompt`, `output_file_path`, `input_images`, `input_audios`, and `input_videos`; it omits `generation_config` for the default empty-schema video model. | R-002, R-003, R-004 | Unit/schema test. |
| AC-004 | When a configured video model has a non-empty parameter schema, `GenerateVideoTool.get_argument_schema()` includes a nested `generation_config` object schema. | R-004 | Unit/schema test with registered fake model. |
| AC-005 | `GenerateVideoTool.execute(...)` splits comma-separated image/audio/video inputs, calls the video client once with the correct lists and prompt, downloads the first returned `video_url`, and returns `{"file_path": ...}`. | R-002, R-005, R-008 | Unit/tool execution test with mocked client/download. |
| AC-006 | If the video client returns no `video_urls`, the tool raises a clear error and does not report a saved file. | R-008 | Unit/error test. |
| AC-007 | `AutobyteusClient.get_available_video_models[_sync]` calls `/models/video`, `generate_video` posts to `/generate-video` with normalized image/audio/video inputs, and `cleanup_video_session` posts to `/cleanup/video`. | R-006 | Unit HTTP client payload/path tests. |
| AC-008 | `AutobyteusVideoModelProvider` registers valid remote video models from configured hosts and skips malformed/no-schema entries consistently with image/audio providers. | R-007 | Unit/provider test with mocked `AutobyteusClient`. |
| AC-009 | `AutobyteusVideoClient.generate_video(...)` passes model name, prompt, image/audio/video inputs, generation config, and session ID to `AutobyteusClient.generate_video`; cleanup calls `cleanup_video_session`. | R-005, R-006 | Unit/client adapter test. |
| AC-010 | Focused tests for existing image/audio import or smoke paths still pass after adding video exports. | R-009 | Existing and/or focused regression tests. |
| AC-011 | With one discovered remote video model named `gemini-omni-app-rpa`, the unqualified default `gemini-omni-app-rpa` resolves to that model; with multiple discovered matches, resolution fails with a clear ambiguity error listing available identifiers. | R-003, R-007 | Unit/factory resolution test. |

## Constraints / Dependencies

- The remote server contract is the sibling `autobyteus_rpa_llm_server` API:
  - `GET /models/video`
  - `POST /generate-video`
  - `POST /cleanup/video`
- `AUTOBYTEUS_API_KEY` remains required by `AutobyteusClient`.
- Remote model discovery depends on `AUTOBYTEUS_LLM_SERVER_HOSTS`; without configured hosts, Autobyteus remote model discovery is skipped.
- Default model identifier is `gemini-omni-app-rpa`.
- Live video generation is not required for default automated tests because it is slow, rate-limited, and requires browser login in the server environment.
- Tests must be run through `uv run python -m pytest`, not bare `pytest`.

## Assumptions

- The sibling server video API released in the previous ticket is the authoritative video-generation backend.
- The initial video backend exposes an empty parameter schema; future server models may expose a non-empty schema and should automatically surface it through the dynamic schema path.
- The public LLM-facing tool argument convention may use comma-separated strings for media inputs to stay consistent with `input_images` in the existing image tool.

## Open Questions / Risks

- Live server validation may be skipped or limited if no local server, API key, or logged-in browser profile is available.
- Existing audio model tests refer to `MultimediaProvider.GOOGLE` even though the enum currently uses `GEMINI`; this appears pre-existing and should not be folded into this ticket unless it blocks required validation.

## Requirement-To-Use-Case Coverage

| Requirement ID | Covered Use Cases |
| --- | --- |
| R-001 | UC-001, UC-002, UC-003, UC-004 |
| R-002 | UC-001, UC-002, UC-003, UC-004 |
| R-003 | UC-001, UC-005 |
| R-004 | UC-001, UC-005 |
| R-005 | UC-001, UC-002, UC-003, UC-004, UC-005 |
| R-006 | UC-001, UC-005 |
| R-007 | UC-005 |
| R-008 | UC-001, UC-002, UC-003, UC-004 |
| R-009 | UC-006 |
| R-010 | UC-001, UC-005, UC-006 |

## Acceptance-Criteria-To-Scenario Intent

| Acceptance Criteria ID | Scenario Intent |
| --- | --- |
| AC-001 | Import/export scenario for public multimedia tools. |
| AC-002 | Registry discovery scenario for the new concrete tool. |
| AC-003 | Default model schema scenario. |
| AC-004 | Non-empty model schema scenario. |
| AC-005 | Successful tool execution delegation and output save scenario. |
| AC-006 | Empty remote result error scenario. |
| AC-007 | Shared HTTP client video endpoint and payload scenario. |
| AC-008 | Remote model discovery scenario. |
| AC-009 | Remote video client adapter scenario. |
| AC-010 | Existing image/audio regression scenario. |
| AC-011 | Default unqualified remote video model resolution scenario. |
