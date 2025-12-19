"""Runtime-aware Gemini model name resolution (API key vs Vertex AI).

Gemini uses different public names for some models between the Developer API
(`gemini-*-*-preview` suffixes) and Vertex AI (no `-preview`). Keeping this
logic separate lets clients stay focused on I/O while we centralize naming
quirks.
"""

import logging

logger = logging.getLogger(__name__)

# Maps Developer API model names to their Vertex AI equivalents by modality.
# As of Dec 18, 2025 the public LLM and image IDs are aligned across runtimes,
# while some TTS variants still differ.
_MODEL_RUNTIME_MAP = {
    "tts": {
        "gemini-2.5-flash-preview-tts": {
            "vertex": "gemini-2.5-flash-tts",
            "api_key": "gemini-2.5-flash-preview-tts",
        },
        "gemini-2.5-pro-preview-tts": {
            "vertex": "gemini-2.5-pro-tts",
            "api_key": "gemini-2.5-pro-preview-tts",
        },
    },
    # For LLM & image the names are currently uniform across runtimes,
    # but the structure is ready should Google introduce divergent aliases.
    "llm": {
        "gemini-3-pro-preview": {
            "vertex": "gemini-3-pro-preview",
            "api_key": "gemini-3-pro-preview",
        },
        "gemini-3-flash-preview": {
            "vertex": "gemini-3-flash-preview",
            "api_key": "gemini-3-flash-preview",
        },
    },
    "image": {
        "gemini-3-pro-image-preview": {
            "vertex": "gemini-3-pro-image-preview",
            "api_key": "gemini-3-pro-image-preview",
        },
        "gemini-2.5-flash-image": {
            "vertex": "gemini-2.5-flash-image",
            "api_key": "gemini-2.5-flash-image",
        },
    },
}


def resolve_model_for_runtime(model_value: str, modality: str, *, runtime: str | None = None) -> str:
    """Return the correct model name for the active Gemini runtime.

    Args:
        model_value: The requested model name (usually from AudioModel.value).
        modality: One of "tts", "llm", "image".
        runtime: Explicit runtime identifier ("vertex" or "api_key").
    """
    if not runtime:
        return model_value

    modality_map = _MODEL_RUNTIME_MAP.get(modality, {})
    runtime_map = modality_map.get(model_value)
    if runtime_map and runtime in runtime_map:
        mapped = runtime_map[runtime]
        if mapped != model_value:
            logger.info("Adjusting Gemini model for runtime '%s': '%s' -> '%s'", runtime, model_value, mapped)
        return mapped

    return model_value
