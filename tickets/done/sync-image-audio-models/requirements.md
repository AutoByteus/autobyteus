# Requirements: Sync Image And Audio Models

Status: Design-ready

## User Intent

Compare the TypeScript Autobyteus implementation at `/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-workspace-superrepo/autobyteus-ts` with the Python library in this repository, identify image and audio models supported in TypeScript but missing in Python, and add Python support for those models.

## Draft Requirements

- Discover the current image and audio model registries/config schemas in `autobyteus-ts`.
- Discover the corresponding Python model registries/config schemas in `autobyteus`.
- Add missing Python support for newly supported image/audio models, with special priority for latest Google image and audio models.
- Add Python image model support for `gemini-3.1-flash-image-preview`.
- Add Python audio model support for `gemini-2.5-pro-tts` using model value `gemini-2.5-pro-preview-tts`.
- Add Python audio model support for `gemini-3.1-flash-tts` using model value `gemini-3.1-flash-tts-preview`.
- Preserve existing Python multimedia client behavior and model identifiers.
- Add or update tests proving the new models are represented in Python and can be surfaced through the image/audio MCP.
- Validate the MCP project can list or otherwise call the updated Python model registry.
- Recheck the Gemini 3.1 TTS official input surface so the Python library and MCP do not hide important model controls from agents.
- Expose official Gemini TTS `languageCode` / SDK `language_code` pass-through when callers need to pin the synthesis language instead of relying only on automatic detection.
- Preserve and document the main Gemini 3.1 TTS control path: rich natural-language prompts, audio tags, speaker-specific transcript labels, and director-style performance guidance.
- Refresh the Google GenAI SDK lock if the current lock is older than the active generated type surface needed for latest Gemini TTS work.
- Recheck the Gemini image official input surface so Google image generation/editing models do not expose empty schemas to MCP agents.
- Expose official Gemini image `image_config.aspect_ratio` and `image_config.image_size` controls for Gemini image models that support them.
- Validate both image generation and image editing using Google image models with the new discovered schema/config path.

## Initial Acceptance Criteria

- The Python image model registry includes the latest Google/Gemini image model `gemini-3.1-flash-image-preview`.
- The Python audio model registry includes `gemini-2.5-pro-tts` and `gemini-3.1-flash-tts`.
- Model metadata, identifiers, provider/runtime fields, default configs, and config schemas match established Python conventions.
- Python tests pass for the touched model registry/client behavior.
- The `autobyteus-image-audio` MCP tests or a targeted MCP validation confirm the new Python models are visible through `list_image_models` and `list_audio_models`.
- `list_audio_models` exposes a Gemini TTS schema that includes `language_code` and describes advanced prompt/audio-tag usage clearly enough for MCP agents.
- The Gemini audio client passes `language_code` to `types.SpeechConfig(language_code=...)` for both single-speaker and multi-speaker modes.
- Credential-free tests cover the new schema field and client config construction behavior.
- `list_image_models` exposes Gemini image schema controls for `image_config.aspect_ratio` and `image_config.image_size`.
- Live validation covers Google image text-to-image and image edit/text-and-image-to-image with `generation_config.image_config`.

## Constraints And Notes

- Do not persist API keys in source, tests, tickets, shell scripts, or docs.
- Live API validation may use an environment variable when needed, but repository tests should not require network credentials.
- Keep compatibility with existing MCP defaults unless a model default change is explicitly justified by the discovered TypeScript behavior.
- Keep official Google API-only fields fixed internally when appropriate. For example, `response_modalities=["AUDIO"]` remains an implementation detail of the speech client, not a user-facing MCP parameter.
