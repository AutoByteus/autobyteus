import sys
import types


def _install_google_genai_stubs():
    """Provide minimal google.genai stubs so the module can import without the SDK."""
    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_types_module = types.ModuleType("google.genai.types")

    class _Placeholder:
        def __init__(self, *args, **kwargs):
            pass

    genai_module.Client = _Placeholder
    genai_module.aio = _Placeholder

    genai_types_module.SpeakerVoiceConfig = _Placeholder
    genai_types_module.VoiceConfig = _Placeholder
    genai_types_module.PrebuiltVoiceConfig = _Placeholder
    genai_types_module.SpeechConfig = _Placeholder
    genai_types_module.MultiSpeakerVoiceConfig = _Placeholder
    genai_types_module.GenerateContentConfig = _Placeholder

    genai_module.types = genai_types_module
    google_module.genai = genai_module

    sys.modules.setdefault("google", google_module)
    sys.modules.setdefault("google.genai", genai_module)
    sys.modules.setdefault("google.genai.types", genai_types_module)


def _install_openai_stub():
    class _Placeholder:
        def __init__(self, *args, **kwargs):
            pass

    openai_module = types.ModuleType("openai")
    openai_module.OpenAI = _Placeholder
    sys.modules.setdefault("openai", openai_module)


_install_google_genai_stubs()
_install_openai_stub()

from autobyteus.utils.gemini_model_mapping import resolve_model_for_runtime


def test_resolves_vertex_model_name():
    resolved = resolve_model_for_runtime("gemini-2.5-flash-preview-tts", modality="tts", runtime="vertex")
    assert resolved == "gemini-2.5-flash-tts"


def test_keeps_preview_for_api_key():
    resolved = resolve_model_for_runtime("gemini-2.5-flash-preview-tts", modality="tts", runtime="api_key")
    assert resolved == "gemini-2.5-flash-preview-tts"


def test_fallback_strip_preview_on_vertex():
    resolved = resolve_model_for_runtime("custom-preview-model", modality="tts", runtime="vertex")
    assert resolved == "custom-model"


def test_llm_model_passthrough_when_names_align():
    resolved = resolve_model_for_runtime("gemini-2.5-pro", modality="llm", runtime="vertex")
    assert resolved == "gemini-2.5-pro"


def test_image_model_passthrough_when_names_align():
    resolved = resolve_model_for_runtime("gemini-2.5-flash-image", modality="image", runtime="api_key")
    assert resolved == "gemini-2.5-flash-image"
