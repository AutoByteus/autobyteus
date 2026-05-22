# Multimedia Tools

Autobyteus exposes multimedia generation tools through the normal tool registry. They use the agent workspace to resolve relative output paths and return the saved local file path after downloading the first generated artifact.

## Available Tools

| Tool | Purpose | Main Inputs | Model Env Var | Default Model |
| --- | --- | --- | --- | --- |
| `generate_image` | Generate or edit an image. | `prompt`, optional comma-separated `input_images`, `output_file_path` | `DEFAULT_IMAGE_GENERATION_MODEL` | `gpt-image-1.5` |
| `edit_image` | Edit an image with an explicit mask or input-image flow. | `prompt`, image inputs, `output_file_path` | `DEFAULT_IMAGE_EDIT_MODEL` | `gpt-image-1.5` |
| `generate_speech` | Generate speech audio from text. | `prompt`, `output_file_path`, optional model `generation_config` | `DEFAULT_SPEECH_GENERATION_MODEL` | `gemini-2.5-flash-tts` |
| `generate_video` | Generate video from text and optional media references. | `prompt`, optional comma-separated `input_images`, `input_audios`, `input_videos`, `output_file_path` | `DEFAULT_VIDEO_GENERATION_MODEL` | `gemini-omni-app-rpa` |

## Video Generation Runtime

`generate_video` uses the `autobyteus.multimedia.video` package. The default `gemini-omni-app-rpa` model is backed by the Autobyteus RPA LLM server and sends requests to the server video API.

The video model registry registers a default local-server model and can also discover server-hosted video models. For RPA-backed models, host-qualified identifiers are exposed as:

```text
<model-name>@<host:port>
```

For example:

```text
gemini-omni-app-rpa@127.0.0.1:8000
```

If `DEFAULT_VIDEO_GENERATION_MODEL` is set to an unqualified model name and exactly one discovered model matches that name, Autobyteus resolves it to that model. If multiple hosts expose the same model name, use the host-qualified identifier to avoid ambiguity.

## Media Inputs

`generate_video` accepts comma-separated strings for each media input field:

```text
input_images="scene_start.png,character_reference.png"
input_audios="voiceover.wav,music_bed.mp3"
input_videos="previous_clip.mp4"
```

Blank entries are ignored. The tool passes these references to the configured video client as image, audio, and video inputs, then downloads the first returned video URL to `output_file_path`.

## Server Configuration

Autobyteus server-backed multimedia clients use the configured RPA LLM server URL. Multi-host discovery for server-backed multimedia models is controlled by `AUTOBYTEUS_LLM_SERVER_HOSTS` when it is set.
