# Proposed Design

## Design Version

- Current Version: `v1`

## Revision History

| Version | Trigger | Summary Of Changes | Related Review Round |
| --- | --- | --- | --- |
| v1 | Initial draft | Add a video multimedia modality that mirrors image/audio and delegates video execution to the Autobyteus RPA LLM server. | Pending |

## Artifact Basis

- Investigation Notes: `tickets/in-progress/video-tool-support/investigation-notes.md`
- Requirements: `tickets/in-progress/video-tool-support/requirements.md`
- Requirements Status: `Refined`
- Policy: `No backward compatibility; remove legacy code paths.`

## Summary

Add video as a first-class multimedia modality in `autobyteus`. The design extends the current image/audio architecture rather than creating a separate path: public tool -> video model registry/factory -> Autobyteus video client adapter -> shared `AutobyteusClient` -> remote RPA LLM server video endpoints.

The implementation does not duplicate Gemini browser automation. The sibling RPA LLM server remains the authoritative execution backend for video generation.

## Goal / Intended Change

- Add a `generate_video` LLM-facing tool.
- Add video model metadata, client factory, provider discovery, and remote client adapter.
- Add shared HTTP client support for `/models/video`, `/generate-video`, and `/cleanup/video`.
- Persist returned videos to the requested local output path using the same helper path as image/audio tools.
- Preserve existing image/audio behavior.

## Requirements And Use Cases

| Requirement ID | Description | Acceptance Criteria ID(s) | Use Case IDs |
| --- | --- | --- | --- |
| R-001 | Concrete `generate_video` multimedia tool. | AC-001, AC-002 | UC-001, UC-002, UC-003, UC-004 |
| R-002 | Required prompt/output and optional image/audio/video inputs. | AC-003, AC-005 | UC-001, UC-002, UC-003, UC-004 |
| R-003 | Configured/default video model resolution, including unique unqualified remote model name fallback. | AC-003, AC-011 | UC-001, UC-005 |
| R-004 | Dynamic generation config only when model metadata exposes parameters. | AC-003, AC-004 | UC-001, UC-005 |
| R-005 | Video execution through multimedia client/factory/provider path and remote server. | AC-005, AC-009 | UC-001, UC-002, UC-003, UC-004, UC-005 |
| R-006 | Shared `AutobyteusClient` video API methods. | AC-007, AC-009 | UC-001, UC-005 |
| R-007 | Remote video model discovery via `AUTOBYTEUS_LLM_SERVER_HOSTS`. | AC-008, AC-011 | UC-005 |
| R-008 | Save generated video with existing download/path helpers. | AC-005, AC-006 | UC-001, UC-002, UC-003, UC-004 |
| R-009 | Existing image/audio behavior remains unchanged. | AC-001, AC-010 | UC-006 |
| R-010 | No backward compatibility shims or duplicate browser/RPA logic. | AC-005, AC-009 | UC-001, UC-005, UC-006 |

## Current-State Read

| Area | Findings | Evidence | Open Unknowns |
| --- | --- | --- | --- |
| Current spine | Image/audio tools already separate tool schemas, model registries, remote clients, and HTTP transport. | `image_tools.py`, `audio_tools.py`, `autobyteus/multimedia/image/*`, `autobyteus/multimedia/audio/*` | None |
| Missing video modality | LLM user messages can carry video, but multimedia generation has no video package or tool. | `media_reader_tool.py`, `AutobyteusClient`, `autobyteus/multimedia/*` | None |
| Remote API contract | Sibling server exposes video model discovery, generation, and cleanup endpoints. | `../autobyteus_rpa_llm_workspace/.../api/endpoints.py`, `api/schemas.py` | Live server availability for optional validation |
| Default model identity | Remote models are host-qualified in `model_identifier`; unqualified default needs deterministic resolution. | `ImageModel.model_identifier`, `AudioModel.model_identifier`, refined R-003 | None |

## Data-Flow Spine Inventory

| Spine ID | Scope | Start | End | Owning Node / Governing Owner | Why It Matters |
| --- | --- | --- | --- | --- | --- |
| DS-001 | Primary End-to-End | `GenerateVideoTool.execute` | Local video file path returned | Multimedia video tool | Main user-facing generation flow. |
| DS-002 | Primary End-to-End | `VideoClientFactory.ensure_initialized` | Registered `VideoModel`s | Multimedia video registry | Makes model-specific schema and execution possible. |
| DS-003 | Bounded Local | `AutobyteusClient.generate_video` | HTTP response JSON | Shared Autobyteus HTTP client | Keeps media normalization and endpoint calls in one authoritative transport boundary. |

## Primary Execution / Data-Flow Spine

`GenerateVideoTool.execute -> VideoClientFactory.create_video_client -> AutobyteusVideoClient.generate_video -> AutobyteusClient.generate_video -> RPA LLM server /generate-video -> download_file_from_url -> local file path`

## Remote Discovery Spine

`VideoClientFactory.ensure_initialized -> register default Autobyteus video model -> AutobyteusVideoModelProvider.discover_and_register -> AutobyteusClient.get_available_video_models_sync -> VideoModel registration`

## Spine Actors / Main-Line Nodes

| Node | Role In Spine | What It Advances |
| --- | --- | --- |
| `GenerateVideoTool` | LLM-facing command boundary | Validates/splits runtime arguments, obtains a client, saves returned media. |
| `VideoClientFactory` | Model construction boundary | Registers and resolves video models, including unique unqualified-name fallback. |
| `VideoModel` | Model metadata | Carries provider, runtime, host URL, parameter schema, and description. |
| `AutobyteusVideoClient` | Remote video adapter | Converts video client interface calls to `AutobyteusClient` calls with session ID. |
| `AutobyteusClient` | HTTP transport boundary | Normalizes media inputs and calls server endpoints. |
| RPA LLM server | Execution backend | Runs browser/RPA video generation and serves generated video URLs. |

## Ownership Map

| Node / Owner | Owns | Must Not Own | Notes |
| --- | --- | --- | --- |
| `autobyteus/tools/multimedia/video_tools.py` | Tool name, descriptions, argument schema, workspace output save | HTTP endpoint details, model discovery internals | Mirrors image/audio tool ownership. |
| `autobyteus/multimedia/video/*` | Video model/client/provider/factory concerns | Generic HTTP client behavior, image/audio model registries | New modality package is justified by existing modality layout. |
| `autobyteus/clients/autobyteus_client.py` | Autobyteus server endpoint methods and media normalization | Tool schemas, model registry decisions | Authoritative HTTP boundary. |
| `autobyteus/utils/download_utils.py` and `file_utils.py` | Existing download/path behavior | Video-specific policy | Reused unchanged. |

## Off-Spine Concerns Around The Spine

| Off-Spine Concern | Serves Which Owner | Responsibility | Must Stay Off Main Line? |
| --- | --- | --- | --- |
| Dynamic `generation_config` schema | `GenerateVideoTool` | Surface model-specific parameters only when present. | Yes |
| Remote host discovery | `VideoClientFactory` | Register server-provided models from configured hosts. | Yes |
| Default unqualified model resolution | `VideoClientFactory` | Resolve `gemini-omni-app-rpa` to a unique matching model or raise clear ambiguity. | Yes |
| Session cleanup | `AutobyteusVideoClient` | Cleanup server session and close HTTP client. | Yes |
| Public exports | Tool and multimedia packages | Make the tool/imports discoverable. | Yes |

## Existing Capability / Subsystem Reuse Check

| Need / Concern | Existing Capability Area / Subsystem | Decision | Why |
| --- | --- | --- | --- |
| Tool schema and registration | `BaseTool`, `ToolMeta`, `ToolRegistry`, `ParameterSchema` | Reuse | Existing class-based tools already self-register and expose lazy schemas. |
| Model registry/factory | `autobyteus/multimedia/image`, `autobyteus/multimedia/audio` patterns | Extend | Video is a peer modality with the same concerns. |
| HTTP transport | `AutobyteusClient` | Extend | It already owns server endpoint calls and media normalization. |
| Output persistence | `download_file_from_url`, `resolve_safe_path` | Reuse | Existing image/audio tools save generated media through these helpers. |

## Architecture Direction Decision

- Chosen direction: Add a peer `video` modality package and `GenerateVideoTool`, extending `AutobyteusClient` for video endpoints.
- Rationale:
  - Complexity: Smallest coherent extension that matches existing image/audio architecture.
  - Testability: Each boundary can be unit tested with mocks.
  - Operability: Uses existing environment variables and server contract.
  - Evolution cost: Future video providers can be added to `VideoClientFactory` without changing the public tool.
- Data-flow spine clarity assessment: `Yes`
- Spine inventory completeness assessment: `Yes`
- Ownership clarity assessment: `Yes`
- Off-spine concern clarity assessment: `Yes`
- Authoritative Boundary Rule assessment: `Yes`
- File placement within owning subsystem assessment: `Yes`
- Outcome: `Add`

## Ownership-Driven Dependency Rules

- Allowed dependency directions:
  - `tools/multimedia/video_tools.py -> multimedia/video -> clients/autobyteus_client.py -> utils/media formatter/httpx`
  - `multimedia/video/video_client_factory.py -> multimedia/video/autobyteus_video_provider.py`
  - `multimedia/video/api/autobyteus_video_client.py -> clients/autobyteus_client.py`
- Authoritative public entrypoints:
  - LLM-facing entrypoint: `GenerateVideoTool`.
  - Model construction entrypoint: `VideoClientFactory.create_video_client`.
  - Server transport entrypoint: `AutobyteusClient`.
- Forbidden shortcuts:
  - Tool code must not call `httpx` or server endpoints directly.
  - Tool code must not import or run sibling RPA browser integrator code.
  - Video client code must not bypass `AutobyteusClient` for media normalization.

## Change Inventory

| Change ID | Change Type | Current Path | Target Path | Rationale |
| --- | --- | --- | --- | --- |
| C-001 | Add | N/A | `autobyteus/multimedia/video/base_video_client.py` | Define video client interface. |
| C-002 | Add | N/A | `autobyteus/multimedia/video/video_model.py` | Define video model metadata and identifier behavior. |
| C-003 | Add | N/A | `autobyteus/multimedia/video/video_client_factory.py` | Register default and discovered video models; construct clients. |
| C-004 | Add | N/A | `autobyteus/multimedia/video/autobyteus_video_provider.py` | Discover `/models/video` from configured server hosts. |
| C-005 | Add | N/A | `autobyteus/multimedia/video/api/autobyteus_video_client.py` | Adapt video client calls to `AutobyteusClient`. |
| C-006 | Add | N/A | `autobyteus/multimedia/video/__init__.py`, `api/__init__.py` | Package exports. |
| C-007 | Modify | `autobyteus/clients/autobyteus_client.py` | Same | Add video discovery/generation/cleanup HTTP methods. |
| C-008 | Modify | `autobyteus/multimedia/utils/response_types.py`, `utils/__init__.py`, `multimedia/__init__.py` | Same | Export video response/model/factory types. |
| C-009 | Add | N/A | `autobyteus/tools/multimedia/video_tools.py` | Add public `generate_video` tool. |
| C-010 | Modify | `autobyteus/tools/multimedia/__init__.py`, `autobyteus/tools/__init__.py` | Same | Export/import `GenerateVideoTool` for discoverability. |
| C-011 | Add/Modify | `tests/unit_tests/...` | New and existing focused tests | Cover AC-001 through AC-011. |

## Removal / Decommission Plan

| Item To Remove / Decommission | Why It Becomes Unnecessary | Replaced By | Scope | Notes |
| --- | --- | --- | --- | --- |
| None | There is no existing video generation implementation in `autobyteus`. | N/A | N/A | This is additive without legacy paths. |

## Draft File Responsibility Mapping

| Candidate File | Owning Subsystem | Owner / Boundary | Concrete Concern | Why This Is One File |
| --- | --- | --- | --- | --- |
| `autobyteus/tools/multimedia/video_tools.py` | Tools / Multimedia | `GenerateVideoTool` | LLM-facing schema, model lookup, input splitting, output save | Matches image/audio tool file layout and keeps tool policy together. |
| `autobyteus/multimedia/video/video_client_factory.py` | Multimedia / Video | Video registry | Default model registration, remote discovery call, client construction, unqualified resolution | Registry behavior belongs at factory boundary. |
| `autobyteus/multimedia/video/autobyteus_video_provider.py` | Multimedia / Video | Remote model discovery | Host parsing, `/models/video` fetch, model registration | Mirrors image/audio providers. |
| `autobyteus/multimedia/video/api/autobyteus_video_client.py` | Multimedia / Video | Remote adapter | Session ID, request delegation, response conversion, cleanup | Mirrors image/audio remote adapters. |
| `autobyteus/clients/autobyteus_client.py` | Clients | HTTP transport | Server endpoint methods and media normalization | Existing authoritative transport owner. |

## Reusable Owned Structures Check

| Repeated Structure / Logic | Candidate Shared File | Decision | Why |
| --- | --- | --- | --- |
| `_get_workspace_root`, `_get_configured_model_identifier`, dynamic schema helpers | Potential shared multimedia tool helper | Keep local for this ticket | Existing duplication already exists between image/audio; extracting now would widen blast radius beyond video support. |
| Model metadata classes | Modality-specific files | Keep modality-specific | Existing architecture uses separate `ImageModel` and `AudioModel`; video should be a peer. |

## Shared Structure / Data Model Tightness Check

| Shared Structure / Type / Schema | One Clear Meaning Per Field? | Redundant Attributes Removed? | Parallel Representation Risk | Decision |
| --- | --- | --- | --- | --- |
| `VideoGenerationResponse(video_urls)` | Yes | Yes | Low | Add as a tight peer to image/audio responses. |
| `VideoModel` | Yes | Yes | Low | Mirror image/audio model metadata, with optional description. |

## Final File Responsibility Mapping

| File | Owning Subsystem | Owner / Boundary | Concrete Concern | Reuses Shared Structure? |
| --- | --- | --- | --- | --- |
| `autobyteus/tools/multimedia/video_tools.py` | Tools / Multimedia | Tool boundary | `GenerateVideoTool`, dynamic video schema, output persistence | `ParameterSchema`, `download_file_from_url`, `resolve_safe_path` |
| `autobyteus/multimedia/video/base_video_client.py` | Multimedia / Video | Interface | Abstract video generation client | `VideoGenerationResponse` |
| `autobyteus/multimedia/video/video_model.py` | Multimedia / Video | Model metadata | Video model registry item and client creation | `MultimediaConfig`, `ParameterSchema` |
| `autobyteus/multimedia/video/video_client_factory.py` | Multimedia / Video | Factory/registry | Register default model, discover remote models, resolve identifiers, create clients | `VideoModel`, `AutobyteusVideoModelProvider` |
| `autobyteus/multimedia/video/autobyteus_video_provider.py` | Multimedia / Video | Remote discovery | Convert `/models/video` responses into `VideoModel`s | `AutobyteusClient` |
| `autobyteus/multimedia/video/api/autobyteus_video_client.py` | Multimedia / Video | Remote adapter | Call remote generate/cleanup endpoints | `AutobyteusClient`, `VideoGenerationResponse` |
| `autobyteus/clients/autobyteus_client.py` | Clients | HTTP transport | Video model, generation, cleanup endpoint methods | Existing media normalization helpers |

## Test Design

| Acceptance Criteria | Test Placement | Strategy |
| --- | --- | --- |
| AC-001, AC-002 | `tests/unit_tests/tools/multimedia/test_video_tools.py` | Import and registry assertions. |
| AC-003, AC-004 | `tests/unit_tests/tools/multimedia/test_video_tools.py` | Schema tests with default and fake parameterized model. |
| AC-005, AC-006 | `tests/unit_tests/tools/multimedia/test_video_tools.py` | Mock video client factory/client and download helper. |
| AC-007 | `tests/unit_tests/clients/test_autobyteus_client.py` | Mock `httpx` clients and media formatter; assert paths/payloads. |
| AC-008 | `tests/unit_tests/multimedia/video/test_autobyteus_video_provider.py` | Mock remote discovery response and registry. |
| AC-009 | `tests/unit_tests/multimedia/video/api/test_autobyteus_video_client.py` | Mock `AutobyteusClient` and assert delegation/cleanup. |
| AC-010 | Focused existing tests/import checks | Run existing client/tool import tests and targeted multimedia tests. |
| AC-011 | `tests/unit_tests/multimedia/video/test_video_client_factory.py` | Register fake host-qualified models and assert unique/ambiguous resolution. |

## Code Review Risk Register

| Risk | Mitigation |
| --- | --- |
| Tool schema fails in environments without live remote discovery | Register a default Autobyteus video model using the first configured/default server URL; remote discovery can overwrite it with richer metadata. |
| Ambiguous multi-host model resolution | Exact identifier wins; unqualified name only works with exactly one matching model. |
| New video imports break existing tools | Keep exports additive and run focused import/registry tests. |
| Live video generation is slow/rate-limited | Default tests mock/contract-test boundaries; optional live validation can be env-gated. |

## Ownership And Structure Checks

| Check | Result | Evidence | Decision |
| --- | --- | --- | --- |
| Existing capability area/subsystem reused or extended | Yes | Video mirrors image/audio under `autobyteus/multimedia` and `tools/multimedia`. | Extend |
| Proposed indirection owns real policy/translation/boundary concern | Yes | Factory resolves models; provider discovers; client adapts HTTP. | Keep |
| Authoritative Boundary Rule preserved | Yes | Tool -> video client/factory -> `AutobyteusClient`; no direct HTTP from tool. | Keep |
| Repeated structures extracted where needed | Yes | `VideoGenerationResponse` is added; other existing helper duplication left untouched to avoid unrelated refactor. | Keep local |
| File placement within owning subsystem | Yes | New files are peers of image/audio equivalents. | Keep |
| No backward-compatibility / legacy path | Yes | No old video generation path exists; no alias/shim planned. | Pass |

## Optional Alternatives

| Option | Summary | Pros | Cons | Decision | Rationale |
| --- | --- | --- | --- | --- | --- |
| A | Add a peer video modality package and tool. | Consistent with existing architecture, testable, clear ownership. | Adds several files. | Chosen | File count reflects established modality pattern. |
| B | Put video directly into existing audio/image modules. | Fewer files. | Mixes modality ownership and makes future provider expansion harder. | Rejected | Violates current structure. |
| C | Tool calls server endpoints directly without video client/factory. | Shorter path. | Bypasses model registry/dynamic schema/provider architecture. | Rejected | Violates authoritative boundary and existing patterns. |
