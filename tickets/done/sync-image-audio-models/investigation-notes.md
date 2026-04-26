# Investigation Notes: Sync Image And Audio Models

Status: Current for Stage 1

## Goals

- Compare multimedia image/audio model support in the TypeScript implementation and the Python library.
- Identify missing Python support for newer Google image and audio models.
- Confirm the MCP validation path for model visibility through `list_image_models` and `list_audio_models`.

## Scope Triage

Scope: Small-to-Medium

Rationale: The change is mostly registry/mapping/test work in existing multimedia model factories. It touches both image and audio capability areas and requires cross-repo MCP validation, but does not require new client architecture because the existing Gemini clients route by model value and already use runtime-aware Gemini model mapping.

## Sources Consulted

### TypeScript Autobyteus

- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-workspace-superrepo/autobyteus-ts/src/multimedia/image/image-client-factory.ts`
  - Built-in image models: `gpt-image-1.5`, `imagen-4`, `gemini-2.5-flash-image`, `gemini-3-pro-image-preview`.
- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-workspace-superrepo/autobyteus-ts/src/multimedia/audio/audio-client-factory.ts`
  - Built-in audio models: `gpt-4o-mini-tts`, `gemini-2.5-flash-tts`.
  - Gemini TTS schema supports `mode`, `voice_name`, `style_instructions`, and `speaker_mapping`.
- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-workspace-superrepo/autobyteus-ts/src/utils/gemini-model-mapping.ts`
  - Runtime mapping includes `gemini-2.5-flash-preview-tts` -> Vertex `gemini-2.5-flash-tts`.
  - Runtime mapping includes `gemini-2.5-pro-preview-tts` -> Vertex `gemini-2.5-pro-tts`, even though the TS audio factory does not currently register a built-in `gemini-2.5-pro-tts` model.
  - Image runtime mapping includes `gemini-3-pro-image-preview` and `gemini-2.5-flash-image`.

### Python Autobyteus

- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models/autobyteus/multimedia/image/image_client_factory.py`
  - Built-in image models currently: `gpt-image-1.5`, `imagen-4`, `gemini-2.5-flash-image`, `gemini-3-pro-image-preview`.
- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models/autobyteus/multimedia/audio/audio_client_factory.py`
  - Built-in audio models currently: `gpt-4o-mini-tts`, `gemini-2.5-flash-tts`.
  - The reusable Gemini TTS schema can be applied to additional Gemini TTS model variants.
- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models/autobyteus/utils/gemini_model_mapping.py`
  - Runtime mapping already contains `gemini-2.5-pro-preview-tts`, but no Python built-in audio model references it yet.
- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models/autobyteus/multimedia/image/api/gemini_image_client.py`
  - Client passes `self.model.value` through `resolve_model_for_runtime(..., modality="image")`.
  - Client can handle image input URLs for conversational image models and text-only prompts for stateless models.
- `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models/autobyteus/multimedia/audio/api/gemini_audio_client.py`
  - Client passes `self.model.value` through `resolve_model_for_runtime(..., modality="tts")`.
  - Client builds single-speaker and multi-speaker `SpeechConfig` from the shared schema.

### Commands Run

- `rg -n "ImageModel|image model|imagen|gemini.*image|gpt-image|nano|banana|Qwen|qwen" -S .` in the TypeScript repo.
- `rg -n "AudioModel|audio model|tts|speech|gemini.*tts|qwen|voice" -S .` in the TypeScript repo.
- `rg -n "class .*Image|ImageModel|imagen|gemini.*image|gpt-image|nano|banana|qwen" -S .` in the Python repo.
- `rg -n "class .*Audio|AudioModel|tts|speech|gemini.*tts|qwen|voice" -S .` in the Python repo.
- `uv run python - <<'PY' ...` in the Python repo to print currently registered API image/audio models.

Current Python registry probe result:

- Image: `gpt-image-1.5`, `imagen-4`, `gemini-2.5-flash-image`, `gemini-3-pro-image-preview`.
- Audio: `gpt-4o-mini-tts`, `gemini-2.5-flash-tts`.

### External / Current Model Facts

- User explicitly clarified that latest Google support must include `gemini-3.1-flash-image-preview`.
- User explicitly confirmed `gemini-2.5-pro-tts` support is required.
- User explicitly confirmed latest support should also include `3.1` TTS; the model value to support is `gemini-3.1-flash-tts-preview`, with the Python-facing model identifier `gemini-3.1-flash-tts`.
- Google AI Gemini model docs list Gemini 3.1 Flash TTS Preview with model code `gemini-3.1-flash-tts-preview`, text input, audio output, and latest update April 2026: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-tts-preview
- Google AI Gemini model docs list Gemini 2.5 Pro Text-to-Speech with model code `gemini-2.5-pro-preview-tts`, text input, audio output, and latest update December 2025: https://ai.google.dev/gemini-api/docs/models/gemini-2.5-pro-preview-tts
- Google AI Gemini model docs list Gemini 3.1 Flash Image Preview with model code `gemini-3.1-flash-image-preview`, text/image input, image/text output, and latest update February 2026: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image-preview
- Google Cloud Vertex AI docs also list Gemini 3.1 Flash Image model ID `gemini-3.1-flash-image-preview`: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-flash-image

## Findings

- Python image support already matches the older TypeScript built-in image registry.
- Python image support is missing latest Google `gemini-3.1-flash-image-preview`.
- Python audio support is missing a built-in model for `gemini-2.5-pro-preview-tts`, despite already having runtime mapping for Developer API and Vertex names.
- Python audio support is missing latest Google `gemini-3.1-flash-tts-preview`.
- No new client class is required for these Google model additions; existing `GeminiImageClient` and `GeminiAudioClient` can route by model value.
- The MCP image/audio server lists models by iterating Python `ImageModel` and `AudioModel`, so registry additions in the Python library should be visible through `list_image_models` and `list_audio_models` once the MCP uses the local updated library.

## Likely File Placement

- Python image registry: `autobyteus/multimedia/image/image_client_factory.py`.
- Python audio registry: `autobyteus/multimedia/audio/audio_client_factory.py`.
- Gemini runtime aliases: `autobyteus/utils/gemini_model_mapping.py`.
- Python tests: existing multimedia factory tests plus targeted assertions for new identifiers.
- MCP validation: `autobyteus_mcps/autobyteus-image-audio` with editable/local dependency or `PYTHONPATH` pointing at this Python worktree.

## Constraints And Implications

- Do not store API keys in committed files. Local `.env.test` exists and is ignored.
- Registry tests should not make network calls or require credentials.
- Live MCP/API validation may use local `.env.test` and should be recorded as executable evidence, but the durable test suite should remain credential-free.
