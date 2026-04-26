# Implementation Plan: Sync Image And Audio Models

Design Version: v1
Status: Implementation Complete

## Scope

Small-to-Medium registry extension using existing multimedia factories and Gemini clients.

## Requirements Mapping

| Requirement ID | Description | Acceptance Criteria | Use Case IDs |
| --- | --- | --- | --- |
| R-001 | Add latest Google image model support. | `gemini-3.1-flash-image-preview` is registered as a Python image model and visible through MCP `list_image_models`. | UC-001 |
| R-002 | Add Google Pro TTS support. | `gemini-2.5-pro-tts` is registered with value `gemini-2.5-pro-preview-tts`, uses the shared Gemini TTS schema, and is visible through MCP `list_audio_models`. | UC-002 |
| R-003 | Add latest Google 3.1 TTS support. | `gemini-3.1-flash-tts` is registered with value `gemini-3.1-flash-tts-preview`, uses the shared Gemini TTS schema, and is visible through MCP `list_audio_models`. | UC-002 |
| R-004 | Preserve existing behavior. | Existing model identifiers and default configs remain unchanged. | UC-001, UC-002 |
| R-005 | Preserve Gemini 3.1 TTS control surface. | Gemini TTS schema exposes `language_code`, preserves single/multi-speaker voice selection, and clearly describes prompt/audio-tag control. | UC-002 |
| R-006 | Keep Google GenAI SDK current enough for latest TTS types. | Lockfile uses the current `google-genai` release checked during the requirement-gap re-entry. | UC-002 |
| R-007 | Preserve Gemini image control surface. | Gemini image schemas expose official `image_config.aspect_ratio`, and Gemini 3 image schemas expose `image_config.image_size`. | UC-001 |

## Data-Flow Spine Inventory

| Spine ID | Scope | Start | End | Owner | Why It Matters |
| --- | --- | --- | --- | --- | --- |
| DS-001 | Bounded Local | `ImageClientFactory.ensure_initialized()` | `ImageModel` registry contains built-in API image models | Image multimedia factory | Controls what image models callers and MCP can discover/create. |
| DS-002 | Bounded Local | `AudioClientFactory.ensure_initialized()` | `AudioModel` registry contains built-in API audio models | Audio multimedia factory | Controls what speech models callers and MCP can discover/create. |
| DS-003 | Primary End-to-End | MCP `list_*_models` tool | JSON model listing returned to MCP caller | MCP server backed by Python multimedia registries | Confirms library registry changes are externally visible. |
| DS-004 | Primary End-to-End | MCP/Python `generate_speech` `generation_config` | Gemini SDK `GenerateContentConfig(speech_config=...)` | Gemini audio client | Ensures agents can use official Gemini TTS config controls without bypassing the MCP. |
| DS-005 | Primary End-to-End | MCP/Python `generate_image` / `edit_image` `generation_config` | Gemini SDK `GenerateContentConfig(image_config=...)` | Gemini image client | Ensures agents can use official Gemini image aspect-ratio and image-size controls for generation and editing. |

## Chosen Design

- Reuse existing `GeminiImageClient` for `gemini-3.1-flash-image-preview`.
- Reuse existing `GeminiAudioClient` and the existing `gemini_tts_schema` for `gemini-2.5-pro-tts` and `gemini-3.1-flash-tts`.
- Add runtime mapping for `gemini-3.1-flash-tts-preview` in `autobyteus/utils/gemini_model_mapping.py`.
- Add optional `language_code` to the shared Gemini TTS schema and pass it into `types.SpeechConfig` for single-speaker and multi-speaker calls.
- Improve Gemini TTS schema and MCP prompt descriptions so agents understand that style, tone, accent, pace, audio tags, and advanced director-style prompts belong in the free-text prompt.
- Update the Google GenAI SDK lock to the current release discovered during the re-entry check.
- Add official Gemini image `image_config` schemas to Gemini image models:
  - Gemini 2.5 Flash Image exposes `aspect_ratio`.
  - Gemini 3 Pro Image Preview and Gemini 3.1 Flash Image Preview expose `aspect_ratio` and `image_size`.
- Add focused tests that assert the new registry entries, values, providers, client classes, and schema defaults.
- Validate MCP model visibility by running the MCP tests or a targeted `list_image_models` / `list_audio_models` session using this Python worktree.

## File Responsibilities

- `autobyteus/multimedia/image/image_client_factory.py`
  - Owns built-in image model registration.
  - Add `gemini-3.1-flash-image-preview` to the existing default image model list.
- `autobyteus/multimedia/audio/audio_client_factory.py`
  - Owns built-in audio model registration and Gemini/OpenAI TTS schema setup.
  - Add `gemini-2.5-pro-tts` and `gemini-3.1-flash-tts` using the existing Gemini TTS schema.
- `autobyteus/utils/gemini_model_mapping.py`
  - Owns runtime-specific Gemini API/Vertex name aliases.
  - Add `gemini-3.1-flash-tts-preview` mapping; existing `gemini-2.5-pro-preview-tts` mapping remains.
- Python tests under `tests/integration_tests/multimedia/...`
  - Assert new model registry metadata without network calls.
- MCP tests/targeted validation in `autobyteus_mcps/autobyteus-image-audio`
  - Confirm the MCP sees the updated Python model registry.

## Validation Plan

- Run focused Python multimedia factory tests.
- Run Python unit/integration tests covering Gemini image model client mapping where applicable.
- Run a targeted MCP model-list validation with `PYTHONPATH` pointing at the Python worktree or by installing the local package in the MCP environment.
- Avoid live audio/image generation unless needed; model visibility is the acceptance criterion for MCP support.

## Execution Tracking

- [x] Add Python image model registry entry.
- [x] Add Python audio model registry entries.
- [x] Add Gemini runtime mapping for `gemini-3.1-flash-tts-preview`.
- [x] Add/update tests.
- [x] Run Python validation.
- [x] Run MCP validation.
- [x] Add Gemini TTS `language_code` schema/client pass-through.
- [x] Refresh `google-genai` lock.
- [x] Add schema/client tests for the official TTS control surface.
- [x] Re-run focused Python and MCP validations.
- [x] Add Gemini image `image_config` schema controls.
- [x] Add schema/client tests for official Gemini image controls.
- [x] Run live Python and MCP image generation/edit validation.

## Implementation Evidence

- Added `gemini-3.1-flash-image-preview` to `autobyteus/multimedia/image/image_client_factory.py`.
- Added `gemini-2.5-pro-tts` and `gemini-3.1-flash-tts` to `autobyteus/multimedia/audio/audio_client_factory.py`.
- Added runtime mapping coverage for `gemini-3.1-flash-tts-preview` and `gemini-3.1-flash-image-preview` in `autobyteus/utils/gemini_model_mapping.py`.
- Added focused Python tests:
  - `tests/integration_tests/multimedia/image/test_image_client_factory.py`
  - `tests/integration_tests/multimedia/audio/test_audio_client_factory.py`
  - `tests/unit_tests/utils/test_gemini_model_mapping.py`
- Added official Gemini TTS control-surface improvements:
  - `language_code` appears in the shared Gemini TTS schema and is passed to `types.SpeechConfig(language_code=...)`.
  - `style_instructions` are wrapped as director's notes plus transcript instead of a bare prefix, reducing the chance the model reads directions aloud.
  - Python tool descriptions and generated Gemini TTS model schemas now call out audio tags and advanced prompt sections; MCP agents receive those details through `list_audio_models`.
  - Multi-speaker config now rejects more than 2 speakers before sending an unsupported request to Gemini.
  - `google-genai` is constrained/refreshed to `>=1.73.1` in `pyproject.toml`/`uv.lock`.
- Added client-level unit tests:
  - `tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py`
- Added official Gemini image control-surface improvements:
  - `gemini-2.5-flash-image` schema exposes `generation_config.image_config.aspect_ratio`.
  - `gemini-3-pro-image-preview` and `gemini-3.1-flash-image-preview` schemas expose `generation_config.image_config.aspect_ratio` and `generation_config.image_config.image_size`.
  - Existing Gemini image client already passed nested `image_config` through to `types.GenerateContentConfig`; new unit tests lock that behavior for both generation and edit calls.
- Added client-level image unit tests:
  - `tests/unit_tests/multimedia/image/api/test_gemini_image_client.py`

## Verification Evidence

- `OPENAI_API_KEY=dummy-openai-key uv run pytest tests/integration_tests/multimedia/image/test_image_client_factory.py tests/integration_tests/multimedia/audio/test_audio_client_factory.py tests/unit_tests/utils/test_gemini_model_mapping.py`
  - Result: `23 passed`
- `OPENAI_API_KEY=dummy-openai-key uv run pytest tests/integration_tests/multimedia/image/test_image_client_factory.py tests/integration_tests/multimedia/audio/test_audio_client_factory.py tests/unit_tests/utils/test_gemini_model_mapping.py tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py`
  - Result: `26 passed`
- `OPENAI_API_KEY=dummy-openai-key uv run pytest tests/integration_tests/multimedia/image/test_image_client_factory.py tests/integration_tests/multimedia/audio/test_audio_client_factory.py tests/unit_tests/utils/test_gemini_model_mapping.py tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py tests/unit_tests/multimedia/image/api/test_gemini_image_client.py`
  - Result: `29 passed`
- Registry probe showed:
  - Image: `gemini-3.1-flash-image-preview`
  - Audio: `gemini-2.5-pro-tts`, `gemini-3.1-flash-tts`
- MCP targeted validation with `PYTHONPATH` pointing at this worktree confirmed:
  - `list_image_models` includes `gemini-3.1-flash-image-preview`
  - `list_audio_models` includes `gemini-2.5-pro-tts` and `gemini-3.1-flash-tts`
  - `list_audio_models` includes `language_code` for the new Gemini TTS models
  - `list_image_models` returns Gemini image `image_config` schemas for `gemini-2.5-flash-image`, `gemini-3-pro-image-preview`, and `gemini-3.1-flash-image-preview`
- Live validation after the SDK/control-surface update confirmed:
  - Python `GenerateSpeechTool` generated audio with `gemini-3.1-flash-tts` and `generation_config.language_code = "en-US"`.
  - MCP `generate_speech` generated audio with `gemini-3.1-flash-tts` and `generation_config.language_code = "en-US"`.
  - Python `GenerateImageTool` still generated an image with `gemini-3.1-flash-image-preview` after the SDK refresh.
  - Python `GenerateImageTool` and `EditImageTool` generated/edited with `gemini-3-pro-image-preview` and `gemini-3.1-flash-image-preview` using `generation_config.image_config`.
  - MCP `generate_image` and `edit_image` generated/edited with `gemini-3-pro-image-preview` and `gemini-3.1-flash-image-preview` using `generation_config.image_config`.
