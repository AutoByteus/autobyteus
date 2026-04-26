# API/E2E Validation: Sync Image And Audio Models

Status: Pass

## Acceptance Criteria Coverage

| Acceptance Criterion | Validation | Result |
| --- | --- | --- |
| Python image registry includes `gemini-3.1-flash-image-preview`. | Focused Python registry test and registry probe. | Passed |
| Python audio registry includes `gemini-2.5-pro-tts`. | Focused Python registry test and registry probe. | Passed |
| Python audio registry includes `gemini-3.1-flash-tts`. | Focused Python registry test and registry probe. | Passed |
| Gemini runtime mapping supports new model values. | `tests/unit_tests/utils/test_gemini_model_mapping.py`. | Passed |
| Python image/audio tools can generate media with the newest Google models. | Live `GenerateImageTool` and `GenerateSpeechTool` smoke tests using ignored `.env.test` Gemini credentials. | Passed |
| MCP can call model listing and see the new models. | Targeted MCP `ClientSession` calling `list_image_models` and `list_audio_models` with `PYTHONPATH` pointed at the Python worktree. | Passed |
| MCP image/audio tools can generate media with the newest Google models. | Live MCP `ClientSession` calls to `generate_image` and `generate_speech` using ignored `.env.test` Gemini credentials. | Passed |
| Existing MCP local tests still pass. | MCP `uv run pytest` with `PYTHONPATH` pointed at the Python worktree. | Passed |
| Gemini TTS schema does not hide official `languageCode` control. | Python schema tests, client unit tests, targeted MCP `list_audio_models` schema probe. | Passed |
| Gemini TTS `language_code` works through Python and MCP generation paths. | Live Python `GenerateSpeechTool` and MCP `generate_speech` calls using `gemini-3.1-flash-tts` with `generation_config.language_code = "en-US"`. | Passed |
| Gemini image schema does not hide official `imageConfig` controls. | Python schema/client tests and targeted MCP `list_image_models` returned-schema probe. | Passed |
| Gemini image generation and edit work with official `image_config` controls. | Live Python and MCP generation/edit calls using `gemini-3-pro-image-preview` and `gemini-3.1-flash-image-preview` with `image_config.aspect_ratio` and `image_config.image_size`. | Passed |

## Commands And Results

### Python Registry And Mapping Tests

```bash
OPENAI_API_KEY=dummy-openai-key uv run pytest \
  tests/integration_tests/multimedia/image/test_image_client_factory.py \
  tests/integration_tests/multimedia/audio/test_audio_client_factory.py \
  tests/unit_tests/utils/test_gemini_model_mapping.py
```

Result: `23 passed`.

### Python Registry Probe

```bash
OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
from autobyteus.multimedia.image import ImageClientFactory, ImageModel
from autobyteus.multimedia.audio import AudioClientFactory, AudioModel
ImageClientFactory.reinitialize()
AudioClientFactory.reinitialize()
...
PY
```

Result included:

- Image: `gemini-3.1-flash-image-preview`
- Audio: `gemini-2.5-pro-tts`, `gemini-3.1-flash-tts`

### Python Live Tool Generation

```bash
set -a
. ./.env.test
set +a
unset VERTEX_AI_API_KEY
unset VERTEX_AI_PROJECT
unset VERTEX_AI_LOCATION
OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
# Calls GenerateImageTool and GenerateSpeechTool with the newest Google models.
PY
```

Result:

- `PASS python-tool image gemini-3.1-flash-image-preview`: `/tmp/autobyteus_stage7_live_tools_pwdo31d1/gemini31_flash_image.png`, `417950` bytes.
- `PASS python-tool audio gemini-3.1-flash-tts`: `/tmp/autobyteus_stage7_live_tools_pwdo31d1/gemini31_flash_tts.wav`, `180524` bytes.
- `PASS python-tool audio gemini-2.5-pro-tts`: `/tmp/autobyteus_stage7_live_tools_pwdo31d1/gemini25_pro_tts.wav`, `278970` bytes.

### Python Control-Surface Tests

```bash
OPENAI_API_KEY=dummy-openai-key uv run pytest \
  tests/integration_tests/multimedia/image/test_image_client_factory.py \
  tests/integration_tests/multimedia/audio/test_audio_client_factory.py \
  tests/unit_tests/utils/test_gemini_model_mapping.py \
  tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py
```

Result: `26 passed`.

### Python Image Control-Surface Tests

```bash
OPENAI_API_KEY=dummy-openai-key uv run pytest \
  tests/unit_tests/multimedia/image/api/test_gemini_image_client.py \
  tests/integration_tests/multimedia/image/test_image_client_factory.py
```

Result: `16 passed`.

### Full Focused Python Validation

```bash
OPENAI_API_KEY=dummy-openai-key uv run pytest \
  tests/integration_tests/multimedia/image/test_image_client_factory.py \
  tests/integration_tests/multimedia/audio/test_audio_client_factory.py \
  tests/unit_tests/utils/test_gemini_model_mapping.py \
  tests/unit_tests/multimedia/audio/api/test_gemini_audio_client.py \
  tests/unit_tests/multimedia/image/api/test_gemini_image_client.py
```

Result: `29 passed`.

### Python Live `language_code` Generation

```bash
set -a
. ./.env.test
set +a
unset VERTEX_AI_API_KEY
unset VERTEX_AI_PROJECT
unset VERTEX_AI_LOCATION
OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
# Calls GenerateSpeechTool with gemini-3.1-flash-tts and generation_config.language_code = "en-US".
# Calls GenerateImageTool with gemini-3.1-flash-image-preview after the SDK refresh.
PY
```

Result:

- `PASS python GenerateSpeechTool language_code`: `/tmp/autobyteus_tts_control_live_tools__fugrhbl/gemini31_tts_language_code.wav`, `236204` bytes.
- `PASS python GenerateImageTool after SDK update`: `/tmp/autobyteus_tts_control_live_tools__fugrhbl/gemini31_image_after_sdk_update.png`, `395323` bytes.

### MCP Targeted Model Listing

```bash
PYTHONPATH="/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models:/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus_mcps/autobyteus-image-audio/src" \
  uv run python - <<'PY'
# Creates MCP server and calls list_image_models/list_audio_models through ClientSession.
PY
```

Result:

- `MCP image models: gemini-3.1-flash-image-preview`
- `MCP audio models: gemini-2.5-pro-tts, gemini-3.1-flash-tts`

### MCP Targeted TTS Schema Probe

```bash
PYTHONPATH="/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models:/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus_mcps/autobyteus-image-audio/src" \
  OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
# Calls list_audio_models and asserts Gemini TTS schemas include language_code.
PY
```

Result:

- `gemini-3.1-flash-tts language_code schema: string`
- `gemini-2.5-pro-tts language_code schema: string`

### MCP `list_audio_models` Returned Schema Shape

The MCP `list_audio_models` payload was captured for:

- `gemini-2.5-flash-tts`
- `gemini-2.5-pro-tts`
- `gemini-3.1-flash-tts`

Each Gemini TTS model returned:

- `default_config`: `{"mode": "single-speaker", "voice_name": "Kore"}`
- `schema_required`: `[]`
- `schema_properties.mode`: string enum `["single-speaker", "multi-speaker"]`, default `single-speaker`
- `schema_properties.voice_name`: string enum with the 30 Gemini voices, default `Kore`
- `schema_properties.language_code`: string with description referencing `SpeechConfig.language_code`
- `schema_properties.style_instructions`: string with director-style guidance, audio tags, and `AUDIO PROFILE` / `SCENE` / `DIRECTOR'S NOTES` / `TRANSCRIPT`
- `schema_properties.speaker_mapping`: array of objects with required `speaker` and `voice`, where `voice` uses the same 30 Gemini voice enum

### MCP `list_image_models` Returned Schema Shape

The MCP `list_image_models` payload was captured for:

- `gemini-2.5-flash-image`
- `gemini-3-pro-image-preview`
- `gemini-3.1-flash-image-preview`

Returned schema shape:

- `gemini-2.5-flash-image`
  - `schema_properties.image_config.aspect_ratio`: enum `["1:1", "1:4", "4:1", "1:8", "8:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]`
- `gemini-3-pro-image-preview`
  - `schema_properties.image_config.aspect_ratio`: same aspect-ratio enum
  - `schema_properties.image_config.image_size`: enum `["512", "1K", "2K", "4K"]`
- `gemini-3.1-flash-image-preview`
  - `schema_properties.image_config.aspect_ratio`: same aspect-ratio enum
  - `schema_properties.image_config.image_size`: enum `["512", "1K", "2K", "4K"]`

### MCP Live Tool Generation

```bash
set -a
. ./.env.test
set +a
unset VERTEX_AI_API_KEY
unset VERTEX_AI_PROJECT
unset VERTEX_AI_LOCATION
PYTHONPATH="/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models:/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus_mcps/autobyteus-image-audio/src" \
  OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
# Creates MCP server and calls generate_image/generate_speech through ClientSession.
PY
```

Result:

- `PASS mcp generate_image gemini-3.1-flash-image-preview`: `/tmp/autobyteus_stage7_live_mcp_595o_md5/mcp_gemini31_flash_image.png`, `273979` bytes.
- `PASS mcp generate_speech gemini-3.1-flash-tts`: `/tmp/autobyteus_stage7_live_mcp_595o_md5/mcp_gemini31_flash_tts.wav`, `238124` bytes.
- `PASS mcp generate_speech gemini-2.5-pro-tts`: `/tmp/autobyteus_stage7_live_mcp_595o_md5/mcp_gemini25_pro_tts.wav`, `355770` bytes.

### Python Live Gemini Image Generation And Edit With `image_config`

```bash
set -a
. ./.env.test
set +a
unset VERTEX_AI_API_KEY
unset VERTEX_AI_PROJECT
unset VERTEX_AI_LOCATION
OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
# Calls GenerateImageTool and EditImageTool with gemini-3-pro-image-preview and
# gemini-3.1-flash-image-preview using generation_config.image_config.
PY
```

Result:

- `PASS python generate gemini-3-pro-image-preview`: `/tmp/autobyteus_google_image_live_tools_qimo_yq8/gemini-3-pro-image-preview_generate.png`, `553223` bytes.
- `PASS python edit gemini-3-pro-image-preview`: `/tmp/autobyteus_google_image_live_tools_qimo_yq8/gemini-3-pro-image-preview_edit.png`, `45811` bytes.
- `PASS python generate gemini-3.1-flash-image-preview`: `/tmp/autobyteus_google_image_live_tools_qimo_yq8/gemini-3_1-flash-image-preview_generate.png`, `493885` bytes.
- `PASS python edit gemini-3.1-flash-image-preview`: `/tmp/autobyteus_google_image_live_tools_qimo_yq8/gemini-3_1-flash-image-preview_edit.png`, `55640` bytes.

### MCP Live Gemini Image Generation And Edit With `image_config`

```bash
set -a
. ./.env.test
set +a
unset VERTEX_AI_API_KEY
unset VERTEX_AI_PROJECT
unset VERTEX_AI_LOCATION
PYTHONPATH="/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models:/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus_mcps/autobyteus-image-audio/src" \
  OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
# Calls MCP generate_image and edit_image with gemini-3-pro-image-preview and
# gemini-3.1-flash-image-preview using generation_config.image_config.
PY
```

Result:

- `PASS MCP generate gemini-3-pro-image-preview`: `/tmp/autobyteus_google_image_live_mcp_889vgdco/gemini-3-pro-image-preview_mcp_generate.png`, `333985` bytes.
- `PASS MCP edit gemini-3-pro-image-preview`: `/tmp/autobyteus_google_image_live_mcp_889vgdco/gemini-3-pro-image-preview_mcp_edit.png`, `108493` bytes.
- `PASS MCP generate gemini-3.1-flash-image-preview`: `/tmp/autobyteus_google_image_live_mcp_889vgdco/gemini-3_1-flash-image-preview_mcp_generate.png`, `366473` bytes.
- `PASS MCP edit gemini-3.1-flash-image-preview`: `/tmp/autobyteus_google_image_live_mcp_889vgdco/gemini-3_1-flash-image-preview_mcp_edit.png`, `108789` bytes.

### MCP Live `language_code` Generation

```bash
set -a
. ./.env.test
set +a
unset VERTEX_AI_API_KEY
unset VERTEX_AI_PROJECT
unset VERTEX_AI_LOCATION
PYTHONPATH="/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models:/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus_mcps/autobyteus-image-audio/src" \
  OPENAI_API_KEY=dummy-openai-key uv run python - <<'PY'
# Calls MCP generate_speech with gemini-3.1-flash-tts and generation_config.language_code = "en-US".
PY
```

Result:

- `PASS MCP generate_speech language_code`: `/tmp/autobyteus_tts_control_live_mcp_t5f8hbfd/mcp_gemini31_tts_language_code.wav`, `278444` bytes.

### MCP Local Tests

```bash
PYTHONPATH="/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus-sync-image-audio-models:/home/ryan-ai/SSD/autobyteus_org_workspace/autobyteus_mcps/autobyteus-image-audio/src" uv run pytest
```

Result: `7 passed, 3 skipped`.

## Residual Risk

- Live validation covered the user-requested newest Google image/audio model paths in both Python tools and the MCP server.
- Residual risk is limited to future Google preview alias changes or API-access changes outside this repository.
