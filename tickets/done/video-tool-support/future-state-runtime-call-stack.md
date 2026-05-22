# Future-State Runtime Call Stacks

## Design Basis

- Scope Classification: `Medium`
- Call Stack Version: `v1`
- Requirements: `tickets/in-progress/video-tool-support/requirements.md` (status `Refined`)
- Source Artifact: `tickets/in-progress/video-tool-support/proposed-design.md`
- Source Design Version: `v1`
- Referenced Sections:
  - `Data-Flow Spine Inventory`
  - `Primary Execution / Data-Flow Spine`
  - `Remote Discovery Spine`
  - `Ownership Map`
  - `Ownership-Driven Dependency Rules`

## Future-State Modeling Rule

This document models the target behavior after implementation. It is not a trace of the current code, because current code has no video-generation modality.

## Use Case Index

| use_case_id | Spine ID(s) | Spine Scope | Governing Owner | Source Type | Requirement ID(s) | Use Case Name | Coverage Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UC-001 | DS-001, DS-003 | Primary End-to-End / Bounded Local | `GenerateVideoTool`, `AutobyteusClient` | Requirement | R-001, R-002, R-003, R-005, R-006, R-008, R-010 | Generate video from prompt | Primary/Error |
| UC-002 | DS-001, DS-003 | Primary End-to-End / Bounded Local | `GenerateVideoTool`, `AutobyteusClient` | Requirement | R-002, R-005, R-006, R-008 | Generate video with image inputs | Primary/Error |
| UC-003 | DS-001, DS-003 | Primary End-to-End / Bounded Local | `GenerateVideoTool`, `AutobyteusClient` | Requirement | R-002, R-005, R-006, R-008 | Generate video with audio inputs | Primary/Error |
| UC-004 | DS-001, DS-003 | Primary End-to-End / Bounded Local | `GenerateVideoTool`, `AutobyteusClient` | Requirement | R-002, R-005, R-006, R-008 | Generate video with video inputs | Primary/Error |
| UC-005 | DS-002 | Primary End-to-End | `VideoClientFactory` | Requirement | R-003, R-004, R-007 | Discover and resolve video models | Primary/Fallback/Error |
| UC-006 | DS-001, DS-002 | Design-Risk / Regression | Existing image/audio owners | Requirement | R-009 | Existing image/audio behavior remains unchanged | Primary |

## Transition Notes

- No temporary migration behavior is required.
- No backward-compatible aliases or legacy fallback branches are introduced.

## Use Case: UC-001 Generate Video From Prompt

### Spine Context

- Spine ID(s): DS-001, DS-003
- Spine Scope: Primary End-to-End plus bounded HTTP client local spine
- Governing Owner: `GenerateVideoTool`
- Why This Use Case Matters: This is the minimum useful public behavior for the new tool.

### Goal

Generate a video from a text prompt and save the returned media to a local path.

### Preconditions

- `GenerateVideoTool` is imported and registered.
- `DEFAULT_VIDEO_GENERATION_MODEL` is unset or points to a resolvable video model.
- `AUTOBYTEUS_API_KEY` is available when the remote `AutobyteusClient` is constructed.
- The selected video model has a valid `host_url`.

### Expected Outcome

The first returned remote `video_url` is downloaded/copied/decoded to the resolved `output_file_path`, and the tool returns `{"file_path": "<resolved path>"}`.

### Primary Runtime Call Stack

```text
[ENTRY] autobyteus/tools/multimedia/video_tools.py:GenerateVideoTool.execute(context, prompt, output_file_path, ...)
└── autobyteus/tools/base_tool.py:BaseTool.execute(...)
    └── [ASYNC] autobyteus/tools/multimedia/video_tools.py:GenerateVideoTool._execute(...)
        ├── autobyteus/tools/multimedia/video_tools.py:_get_configured_model_identifier("DEFAULT_VIDEO_GENERATION_MODEL", "gemini-omni-app-rpa")
        ├── autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory.create_video_client(model_identifier)
        │   ├── autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory.ensure_initialized()
        │   ├── autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory._resolve_model(model_identifier)
        │   └── autobyteus/multimedia/video/video_model.py:VideoModel.create_client(...)
        │       └── autobyteus/multimedia/video/api/autobyteus_video_client.py:AutobyteusVideoClient.__init__(model, config) [STATE]
        │           ├── autobyteus/clients/autobyteus_client.py:AutobyteusClient(server_url=model.host_url)
        │           └── uuid.uuid4() -> session_id [STATE]
        ├── autobyteus/tools/multimedia/video_tools.py:_split_media_inputs(None) -> []
        ├── [ASYNC] autobyteus/multimedia/video/api/autobyteus_video_client.py:AutobyteusVideoClient.generate_video(...)
        │   └── [ASYNC] autobyteus/clients/autobyteus_client.py:AutobyteusClient.generate_video(...)
        │       ├── [ASYNC] AutobyteusClient._normalize_media_sources([]) -> [] [STATE]
        │       ├── [IO] httpx.AsyncClient.post("{server_url}/generate-video", json={model_name, prompt, input_image_urls: [], input_audio_urls: [], input_video_urls: [], generation_config: {}, session_id})
        │       └── response.json() -> {"video_urls": [...]} [STATE]
        ├── autobyteus/multimedia/utils/response_types.py:VideoGenerationResponse(video_urls=response_data["video_urls"])
        ├── autobyteus/tools/multimedia/video_tools.py:_get_workspace_root(context)
        ├── autobyteus/utils/file_utils.py:resolve_safe_path(output_file_path, workspace_root)
        ├── [ASYNC][IO] autobyteus/utils/download_utils.py:download_file_from_url(video_urls[0], resolved_path)
        └── return {"file_path": str(resolved_path)}
```

### Branching / Fallback Paths

```text
[FALLBACK] DEFAULT_VIDEO_GENERATION_MODEL unset
GenerateVideoTool._execute(...)
└── _get_configured_model_identifier(...) -> "gemini-omni-app-rpa"
    └── VideoClientFactory._resolve_model("gemini-omni-app-rpa")
        ├── exact match if present
        └── unique name match among registered video models if exact match absent
```

```text
[ERROR] no video URLs returned
AutobyteusVideoClient.generate_video(...)
└── response_data.get("video_urls", []) == []
    └── raise ValueError("Remote Autobyteus server did not return any video URLs.")
```

```text
[ERROR] output_file_path missing
GenerateVideoTool._execute(...)
└── if not output_file_path
    └── raise ValueError("output_file_path is required but was not provided.")
```

### State And Data Transformations

- Tool arguments -> model identifier, media lists, output path.
- Local paths/URLs/data URIs -> normalized data URIs in `AutobyteusClient`.
- Server response JSON -> `VideoGenerationResponse`.
- Remote media URL/data URI/local path -> saved local video file.

### Observability And Debug Points

- Tool logs selected model identifier.
- Video client logs host/model/session ID.
- HTTP client wraps HTTP status errors through `_wrap_http_error`.

### Design Smells / Gaps

- Legacy/backward-compatibility branch present: `No`
- Tight coupling or cyclic cross-subsystem dependency introduced: `No`
- Naming-to-responsibility drift detected: `No`

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `Covered`
- Error Path: `Covered`

## Use Case: UC-002 Generate Video With Image Inputs

### Spine Context

- Spine ID(s): DS-001, DS-003
- Spine Scope: Primary End-to-End plus bounded HTTP client local spine
- Governing Owner: `GenerateVideoTool`

### Goal

Pass one or more image references to the video backend.

### Preconditions

- Same as UC-001.
- `input_images` is a comma-separated string of local paths, URLs, or data URIs.

### Expected Outcome

The tool sends `input_image_urls` as a list to the video client, and `AutobyteusClient.generate_video` normalizes each image source before posting to `/generate-video`.

### Primary Runtime Call Stack

```text
[ENTRY] GenerateVideoTool.execute(..., input_images="a.png, https://example.com/b.png")
└── [ASYNC] GenerateVideoTool._execute(...)
    ├── autobyteus/tools/multimedia/video_tools.py:_split_media_inputs(input_images) -> ["a.png", "https://example.com/b.png"]
    ├── [ASYNC] AutobyteusVideoClient.generate_video(prompt, input_image_urls=[...], input_audio_urls=[], input_video_urls=[], ...)
    └── [ASYNC] AutobyteusClient.generate_video(...)
        ├── [ASYNC] _normalize_media_sources(input_image_urls) -> ["data:image/...", "data:image/..."]
        └── [IO] POST /generate-video with normalized input_image_urls
```

### Branching / Fallback Paths

```text
[FALLBACK] blank entries in comma-separated input
_split_media_inputs("a.png, , b.png")
└── trims and drops empty entries -> ["a.png", "b.png"]
```

### State And Data Transformations

- Comma-separated string -> list of trimmed image sources.
- Image source list -> normalized data URI list.

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `Covered`
- Error Path: `Covered by UC-001 shared error branches`

## Use Case: UC-003 Generate Video With Audio Inputs

### Spine Context

- Spine ID(s): DS-001, DS-003
- Spine Scope: Primary End-to-End plus bounded HTTP client local spine
- Governing Owner: `GenerateVideoTool`

### Goal

Pass one or more audio references to the video backend.

### Preconditions

- Same as UC-001.
- `input_audios` is a comma-separated string of local paths, URLs, or data URIs.

### Expected Outcome

The tool sends `input_audio_urls` as a list to the video client, and `AutobyteusClient.generate_video` normalizes each audio source before posting to `/generate-video`.

### Primary Runtime Call Stack

```text
[ENTRY] GenerateVideoTool.execute(..., input_audios="voice.wav, music.mp3")
└── [ASYNC] GenerateVideoTool._execute(...)
    ├── _split_media_inputs(input_audios) -> ["voice.wav", "music.mp3"]
    ├── [ASYNC] AutobyteusVideoClient.generate_video(prompt, input_audio_urls=[...], ...)
    └── [ASYNC] AutobyteusClient.generate_video(...)
        ├── [ASYNC] _normalize_media_sources(input_audio_urls) -> ["data:audio/...", "data:audio/..."]
        └── [IO] POST /generate-video with normalized input_audio_urls
```

### Branching / Fallback Paths

```text
[FALLBACK] audio input omitted
GenerateVideoTool._execute(..., input_audios=None)
└── _split_media_inputs(None) -> []
```

### State And Data Transformations

- Comma-separated string -> list of trimmed audio sources.
- Audio source list -> normalized data URI list.

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `Covered`
- Error Path: `Covered by UC-001 shared error branches`

## Use Case: UC-004 Generate Video With Video Inputs

### Spine Context

- Spine ID(s): DS-001, DS-003
- Spine Scope: Primary End-to-End plus bounded HTTP client local spine
- Governing Owner: `GenerateVideoTool`

### Goal

Pass one or more video references to the backend, for continuation/reference workflows.

### Preconditions

- Same as UC-001.
- `input_videos` is a comma-separated string of local paths, URLs, or data URIs.

### Expected Outcome

The tool sends `input_video_urls` as a list to the video client, and `AutobyteusClient.generate_video` normalizes each video source before posting to `/generate-video`.

### Primary Runtime Call Stack

```text
[ENTRY] GenerateVideoTool.execute(..., input_videos="scene1.mp4")
└── [ASYNC] GenerateVideoTool._execute(...)
    ├── _split_media_inputs(input_videos) -> ["scene1.mp4"]
    ├── [ASYNC] AutobyteusVideoClient.generate_video(prompt, input_video_urls=["scene1.mp4"], ...)
    └── [ASYNC] AutobyteusClient.generate_video(...)
        ├── [ASYNC] _normalize_media_sources(input_video_urls) -> ["data:video/mp4;base64,..."]
        └── [IO] POST /generate-video with normalized input_video_urls
```

### Branching / Fallback Paths

```text
[ERROR] media source normalization fails
AutobyteusClient._normalize_media_sources(input_video_urls)
└── media_source_to_data_uri(source) raises
    └── propagate as generation request failure
```

### State And Data Transformations

- Comma-separated string -> list of trimmed video sources.
- Video source list -> normalized data URI list.

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `N/A`
- Error Path: `Covered`

## Use Case: UC-005 Discover And Resolve Video Models

### Spine Context

- Spine ID(s): DS-002
- Spine Scope: Primary End-to-End
- Governing Owner: `VideoClientFactory`
- Why This Use Case Matters: Tool schemas and execution depend on resolvable video model metadata.

### Goal

Initialize the video model registry with a usable default and any server-discovered video models.

### Preconditions

- `VideoClientFactory.ensure_initialized()` is called by schema building, `VideoModel` access, or client creation.
- `AUTOBYTEUS_LLM_SERVER_HOSTS` may be unset, single-host, or multi-host.

### Expected Outcome

The registry contains a default Autobyteus video model. If hosts are configured, server-provided `/models/video` entries are registered with host-qualified identifiers and any returned schema/description.

### Primary Runtime Call Stack

```text
[ENTRY] autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory.ensure_initialized()
└── autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory._initialize_registry()
    ├── autobyteus/clients/autobyteus_client.py:AutobyteusClient._get_default_server_url_from_env()
    ├── autobyteus/multimedia/video/video_model.py:VideoModel(name="gemini-omni-app-rpa", value="gemini-omni-app", provider=AUTOBYTEUS, runtime=AUTOBYTEUS, host_url=default_server_url, parameter_schema=None)
    ├── autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory.register_model(default_model) [STATE]
    └── autobyteus/multimedia/video/autobyteus_video_provider.py:AutobyteusVideoModelProvider.discover_and_register()
        ├── AutobyteusVideoModelProvider._get_hosts() -> configured hosts
        ├── for each host: AutobyteusVideoModelProvider.is_valid_url(host)
        ├── autobyteus/clients/autobyteus_client.py:AutobyteusClient(server_url=host)
        ├── [IO] AutobyteusClient.get_available_video_models_sync() -> GET /models/video
        ├── for each model_info: VideoModel(...)
        └── VideoClientFactory.register_model(video_model) [STATE]
```

### Branching / Fallback Paths

```text
[FALLBACK] no AUTOBYTEUS_LLM_SERVER_HOSTS
AutobyteusVideoModelProvider._get_hosts() -> []
└── discovery skipped; default video model remains registered with AutobyteusClient default server URL
```

```text
[FALLBACK] unqualified default model resolution
VideoClientFactory._resolve_model("gemini-omni-app-rpa")
├── if exact identifier exists: return exact model
├── else collect models where model.name == "gemini-omni-app-rpa"
├── if exactly one match: return that model
└── if multiple matches: raise ValueError with available identifiers
```

```text
[ERROR] malformed server model
AutobyteusVideoModelProvider.discover_and_register()
└── if model_info lacks name/value/provider or parameter_schema
    └── skip model and continue host processing
```

```text
[ERROR] remote discovery fetch fails
AutobyteusVideoModelProvider.discover_and_register()
└── AutobyteusClient.get_available_video_models_sync() raises
    └── log warning and continue next host; default model remains
```

### State And Data Transformations

- Host URLs -> host-qualified model identifiers through `VideoModel.model_identifier`.
- Server `parameter_schema` dict -> `ParameterSchema`.
- Server `description` -> `VideoModel.description`.

### Observability And Debug Points

- Factory logs registry initialization and model registration.
- Provider logs invalid hosts, fetch failures, skipped malformed models, and successful registration counts.

### Design Smells / Gaps

- Legacy/backward-compatibility branch present: `No`
- Tight coupling or cyclic cross-subsystem dependency introduced: `No`
- Naming-to-responsibility drift detected: `No`

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `Covered`
- Error Path: `Covered`

## Use Case: UC-006 Existing Image/Audio Behavior Remains Unchanged

### Spine Context

- Spine ID(s): DS-001, DS-002 as regression-adjacent spines
- Spine Scope: Design-risk / regression
- Governing Owner: Existing image/audio owners
- Why This Use Case Matters: Video is a separate modality and must not alter existing functionality.

### Goal

Ensure adding video imports/exports does not change existing image/audio behavior.

### Preconditions

- Existing modules import successfully.
- Existing tests can still resolve image/audio models and tools.

### Expected Outcome

Image/audio classes, factories, default model behavior, and exports continue to work.

### Primary Runtime Call Stack

```text
[ENTRY] import autobyteus.tools.multimedia
├── autobyteus/tools/multimedia/__init__.py imports GenerateImageTool, EditImageTool, GenerateSpeechTool, GenerateVideoTool, ReadMediaFile, DownloadMediaTool
├── autobyteus/tools/tool_meta.py:ToolMeta.__init__(GenerateImageTool) [STATE] # unchanged
├── autobyteus/tools/tool_meta.py:ToolMeta.__init__(EditImageTool) [STATE] # unchanged
├── autobyteus/tools/tool_meta.py:ToolMeta.__init__(GenerateSpeechTool) [STATE] # unchanged
└── autobyteus/tools/tool_meta.py:ToolMeta.__init__(GenerateVideoTool) [STATE] # new additive registration
```

```text
[ENTRY] existing GenerateImageTool.get_argument_schema()
└── existing image dynamic schema path remains unchanged

[ENTRY] existing GenerateSpeechTool.get_argument_schema()
└── existing audio dynamic schema path remains unchanged
```

### Branching / Fallback Paths

```text
[ERROR] optional multimedia dependency missing
autobyteus/tools/__init__.py optional import guard
└── video import failure sets GenerateVideoTool = None without changing existing image import guard behavior
```

### State And Data Transformations

- No image/audio data transformations change.

### Observability And Debug Points

- Existing import warnings remain module-specific.

### Design Smells / Gaps

- Legacy/backward-compatibility branch present: `No`
- Tight coupling or cyclic cross-subsystem dependency introduced: `No`
- Naming-to-responsibility drift detected: `No`

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `Covered`
- Error Path: `N/A`

## Cross-Cutting Schema Runtime

### Tool Schema Build Stack

```text
[ENTRY] autobyteus/tools/multimedia/video_tools.py:GenerateVideoTool.get_argument_schema()
├── base params: prompt, input_images, input_audios, input_videos, output_file_path
├── autobyteus/tools/multimedia/video_tools.py:_build_dynamic_video_schema(base_params, model_env_var, default_model)
│   ├── _get_configured_model_identifier(...)
│   ├── autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory.ensure_initialized()
│   ├── autobyteus/multimedia/video/video_client_factory.py:VideoClientFactory.get_model(model_identifier)
│   └── if model.parameter_schema.parameters:
│       └── add ParameterDefinition(name="generation_config", param_type=OBJECT, object_schema=model.parameter_schema)
└── return ParameterSchema
```

### Schema Branches

```text
[FALLBACK] selected model has empty parameter_schema
_build_dynamic_video_schema(...)
└── do not add generation_config
```

```text
[ERROR] selected model cannot be resolved
VideoClientFactory.get_model(model_identifier)
└── raise ValueError with available model identifiers and ambiguity details if applicable
```

## Coverage Closure

| Requirement ID | Runtime Use Case Coverage |
| --- | --- |
| R-001 | UC-001, UC-006 |
| R-002 | UC-001, UC-002, UC-003, UC-004 |
| R-003 | UC-001, UC-005, Cross-Cutting Schema Runtime |
| R-004 | UC-005, Cross-Cutting Schema Runtime |
| R-005 | UC-001, UC-002, UC-003, UC-004 |
| R-006 | UC-001, UC-002, UC-003, UC-004, UC-005 |
| R-007 | UC-005 |
| R-008 | UC-001, UC-002, UC-003, UC-004 |
| R-009 | UC-006 |
| R-010 | All use cases: no duplicated RPA/browser logic or compatibility branches. |
