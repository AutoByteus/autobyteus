# Future-State Runtime Call Stacks

## Design Basis

- Scope Classification: Small-to-Medium
- Call Stack Version: v1
- Requirements: `tickets/in-progress/sync-image-audio-models/requirements.md`
- Source Artifact: `tickets/in-progress/sync-image-audio-models/implementation.md`
- Source Design Version: v1

## Use Case Index

| use_case_id | Spine ID(s) | Spine Scope | Governing Owner | Source Type | Requirement ID(s) | Use Case Name | Coverage Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UC-001 | DS-001, DS-003 | Bounded Local + Primary End-to-End | Image multimedia factory / MCP server | Requirement | R-001, R-004 | Discover latest Google image model | Primary/Error |
| UC-002 | DS-002, DS-003 | Bounded Local + Primary End-to-End | Audio multimedia factory / MCP server | Requirement | R-002, R-003, R-004 | Discover latest Google audio models | Primary/Error |

## Use Case: UC-001 Discover Latest Google Image Model

### Goal

Register `gemini-3.1-flash-image-preview` as a built-in Python image model and expose it through library and MCP model listing.

### Preconditions

- Python process imports `autobyteus.multimedia.image`.
- No remote Autobyteus host discovery is required for built-in API models.

### Primary Runtime Call Stack

```text
[ENTRY] caller:list(ImageModel) or ImageClientFactory.create_image_client("gemini-3.1-flash-image-preview")
├── autobyteus/multimedia/image/image_model.py:ImageModelMeta.__iter__ or __getitem__
├── autobyteus/multimedia/image/image_client_factory.py:ImageClientFactory.ensure_initialized()
│   ├── autobyteus/multimedia/image/image_client_factory.py:ImageClientFactory._initialize_registry()
│   │   ├── autobyteus/multimedia/image/image_model.py:ImageModel(...) [STATE]
│   │   └── autobyteus/multimedia/image/image_client_factory.py:ImageClientFactory.register_model(...) [STATE]
│   └── autobyteus/multimedia/image/autobyteus_image_provider.py:discover_and_register() [FALLBACK remote discovery, not required]
└── caller receives built-in ImageModel or GeminiImageClient
```

### MCP Visibility Path

```text
[ENTRY] autobyteus-image-audio MCP:list_image_models
├── image_audio_mcp/server.py:list_image_models(...)
├── autobyteus/multimedia/image/image_client_factory.py:ImageClientFactory.ensure_initialized()
├── autobyteus/multimedia/image/image_model.py:ImageModelMeta.__iter__
└── MCP structured output includes "gemini-3.1-flash-image-preview"
```

### Error Path

```text
[ERROR] caller requests misspelled image model
autobyteus/multimedia/image/image_client_factory.py:create_image_client(...)
└── raises ValueError with available model identifiers
```

### State And Data Transformations

- Registry construction converts hard-coded `ImageModel(...)` definitions into `_models_by_identifier` entries.
- MCP listing converts `ImageModel` objects into structured dictionaries.

### Coverage Status

- Primary Path: Covered by registry tests and MCP targeted validation.
- Fallback Path: N/A for built-in models.
- Error Path: Existing invalid identifier test remains.

## Use Case: UC-002 Discover Latest Google Audio Models

### Goal

Register `gemini-2.5-pro-tts` and `gemini-3.1-flash-tts` as built-in Python audio models and expose them through library and MCP model listing.

### Preconditions

- Python process imports `autobyteus.multimedia.audio`.
- No live Gemini API call is required for registry visibility.

### Primary Runtime Call Stack

```text
[ENTRY] caller:list(AudioModel) or AudioClientFactory.create_audio_client("gemini-3.1-flash-tts")
├── autobyteus/multimedia/audio/audio_model.py:AudioModelMeta.__iter__ or __getitem__
├── autobyteus/multimedia/audio/audio_client_factory.py:AudioClientFactory.ensure_initialized()
│   ├── autobyteus/multimedia/audio/audio_client_factory.py:AudioClientFactory._initialize_registry()
│   │   ├── autobyteus/multimedia/audio/audio_model.py:AudioModel(...) [STATE]
│   │   └── autobyteus/multimedia/audio/audio_client_factory.py:AudioClientFactory.register_model(...) [STATE]
│   └── autobyteus/multimedia/audio/autobyteus_audio_provider.py:discover_and_register() [FALLBACK remote discovery, not required]
└── caller receives built-in AudioModel or GeminiAudioClient
```

### Runtime Alias Path For Live Calls

```text
[ENTRY] GeminiAudioClient.generate_speech(...)
├── autobyteus/multimedia/audio/api/gemini_audio_client.py:generate_speech(...)
├── autobyteus/utils/gemini_model_mapping.py:resolve_model_for_runtime(model.value, modality="tts", runtime=...)
│   ├── [FALLBACK] api_key runtime keeps preview model value
│   └── [FALLBACK] vertex runtime maps to Vertex alias when configured
└── google.genai client generate_content(...) [IO]
```

### MCP Visibility Path

```text
[ENTRY] autobyteus-image-audio MCP:list_audio_models
├── image_audio_mcp/server.py:list_audio_models(...)
├── autobyteus/multimedia/audio/audio_client_factory.py:AudioClientFactory.ensure_initialized()
├── autobyteus/multimedia/audio/audio_model.py:AudioModelMeta.__iter__
└── MCP structured output includes "gemini-2.5-pro-tts" and "gemini-3.1-flash-tts"
```

### Error Path

```text
[ERROR] caller requests misspelled audio model
autobyteus/multimedia/audio/audio_client_factory.py:create_audio_client(...)
└── raises ValueError with available model identifiers
```

### State And Data Transformations

- Shared Gemini TTS `ParameterSchema` is attached to every Gemini TTS built-in model.
- Runtime alias resolution maps Python model value to the appropriate Google runtime name for live calls.
- MCP listing converts `AudioModel` objects into structured dictionaries including schemas and default configs.

### Coverage Status

- Primary Path: Covered by registry tests and MCP targeted validation.
- Fallback Path: Covered by runtime mapping unit/focused test.
- Error Path: Existing invalid identifier test remains.
