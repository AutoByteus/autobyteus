# Handoff Summary: Sync Image And Audio Models

Status: Awaiting User Verification

## What Changed

- Added Python image model support for `gemini-3.1-flash-image-preview`.
- Added Python audio model support for:
  - `gemini-2.5-pro-tts` -> `gemini-2.5-pro-preview-tts`
  - `gemini-3.1-flash-tts` -> `gemini-3.1-flash-tts-preview`
- Added Gemini runtime mapping coverage for the new 3.1 image/audio values.
- Added focused Python tests for registry and runtime mapping.
- Verified the MCP can call `list_image_models` and `list_audio_models` and see the new models when using this Python worktree.
- Verified direct Python tools can generate real media with `gemini-3.1-flash-image-preview`, `gemini-3.1-flash-tts`, and `gemini-2.5-pro-tts`.
- Verified MCP `generate_image` and `generate_speech` can generate real media with those same Google models when using this Python worktree.
- Added Gemini TTS `language_code` schema/pass-through so agents can use official `SpeechConfig.language_code` instead of relying only on auto-detection.
- Improved Gemini TTS prompt/config schema guidance for audio tags, director-style instructions, multi-speaker limits, and advanced prompt sections.
- Added Gemini image `image_config` schemas so agents can discover official `aspect_ratio` and, for Gemini 3 image models, `image_size`.
- Refreshed the Python Google GenAI SDK lock to `google-genai 1.73.1`.
- Aligned `uv.lock` editable package version with `pyproject.toml` (`1.4.2`).

## Validation

- Python focused tests: `29 passed`.
- MCP local tests with updated Python worktree on `PYTHONPATH`: `7 passed, 3 skipped`.
- MCP targeted model-list session: passed.
- MCP `list_audio_models` returned schema validation: passed; Gemini TTS models return `mode`, `voice_name`, `style_instructions`, `language_code`, and `speaker_mapping`.
- MCP `list_image_models` returned schema validation: passed; Gemini image models return `image_config.aspect_ratio`, and Gemini 3 image models return `image_config.image_size`.
- Python live tool generation: passed for `gemini-3.1-flash-image-preview`, `gemini-3.1-flash-tts`, and `gemini-2.5-pro-tts`.
- MCP live generation: passed for `gemini-3.1-flash-image-preview`, `gemini-3.1-flash-tts`, and `gemini-2.5-pro-tts`.
- Python and MCP live `language_code` generation: passed with `gemini-3.1-flash-tts` and `language_code = "en-US"`.
- Python live image generation/edit: passed for `gemini-3-pro-image-preview` and `gemini-3.1-flash-image-preview` with `generation_config.image_config`.
- MCP live image generation/edit: passed for `gemini-3-pro-image-preview` and `gemini-3.1-flash-image-preview` with `generation_config.image_config`.
- `git diff --check`: passed.

## Not Done / Residual Risk

- The user-requested newest Google image/audio model paths have live generation coverage through both Python tools and MCP.
- Current Google docs list `ReplicatedVoiceConfig` nowhere in the official TTS guide/API reference; although the latest SDK exposes that type, it was not added to the MCP schema without an official supported TTS path.
- Remaining risk is external Google preview model/API alias or access changes after this validation run.

## Release Notes

Release notes are required because the user requested package finalization/release. See `release-notes.md`.

## Stage 10 State

The user explicitly confirmed ticket finalization. Stage 10 repository finalization/release is in progress.
