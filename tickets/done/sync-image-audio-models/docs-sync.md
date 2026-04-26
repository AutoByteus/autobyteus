# Docs Sync: Sync Image And Audio Models

Status: Pass

## Long-Lived Docs Check

Checked:

- `README.md`
- `ARCHITECTURE.md`
- `GEMINI.md`
- `AGENTS.md`
- `docs/`

Searches:

- `rg -n "gemini-2\\.5-flash-tts|gemini-2\\.5-pro-tts|gemini-3\\.1-flash|gemini-3-pro-image|imagen-4|gpt-image|multimedia|image model|audio model|TTS" README.md docs ARCHITECTURE.md GEMINI.md AGENTS.md`
- `rg -n "multimedia|ImageClientFactory|AudioClientFactory|ImageModel|AudioModel" README.md docs ARCHITECTURE.md GEMINI.md AGENTS.md`

Result: no long-lived project docs enumerate supported multimedia image/audio models or model IDs.

## Decision

No long-lived docs update required. The source registry, tests, workflow artifacts, and MCP validation evidence are the authoritative record for this task.

Stage 9 was rechecked after the Stage 7 validation-gap re-entry. The added live Python tool and MCP generation evidence changes validation artifacts only; it does not create a new long-lived documentation surface to update.

Stage 9 was rechecked again after the Gemini TTS control-surface requirement-gap re-entry. The new user-facing behavior is discoverable through `list_audio_models` and the Python tool schema; this repository still has no separate long-lived supported multimedia model or Gemini TTS parameter document to update.

Stage 9 was rechecked after the Gemini image control-surface requirement-gap re-entry. The new user-facing image controls are discoverable through `list_image_models`; this repository still has no separate long-lived supported multimedia model or Gemini image parameter document to update.

## External Source Sync

Updated `investigation-notes.md` with official Google model documentation links used for current model names:

- Gemini 3.1 Flash TTS Preview
- Gemini 2.5 Pro Text-to-Speech
- Gemini 3.1 Flash Image Preview
- Vertex AI Gemini 3.1 Flash Image
