# Release Notes: Autobyteus 1.4.3

## Highlights

- Add Gemini 3.1 Flash Image Preview support.
- Add Gemini 2.5 Pro TTS and Gemini 3.1 Flash TTS support.
- Expose Gemini TTS `language_code` and richer prompt-control guidance through audio model schemas.
- Expose official Gemini image `image_config.aspect_ratio` and Gemini 3 `image_config.image_size` controls through image model schemas.
- Refresh `google-genai` to `1.73.1`.

## Validation

- Focused Python validation: `29 passed`.
- Image/audio MCP validation with this Autobyteus worktree: `7 passed, 3 skipped`.
- Live Gemini TTS generation with `language_code`: passed through Python and MCP.
- Live Gemini image generation and edit: passed through Python and MCP for `gemini-3-pro-image-preview` and `gemini-3.1-flash-image-preview`.
