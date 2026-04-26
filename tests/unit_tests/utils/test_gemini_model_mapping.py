from autobyteus.utils.gemini_model_mapping import resolve_model_for_runtime


def test_resolves_gemini_pro_tts_vertex_alias():
    assert (
        resolve_model_for_runtime(
            "gemini-2.5-pro-preview-tts",
            "tts",
            runtime="vertex",
        )
        == "gemini-2.5-pro-tts"
    )


def test_resolves_gemini_31_flash_tts_runtime_names():
    assert (
        resolve_model_for_runtime(
            "gemini-3.1-flash-tts-preview",
            "tts",
            runtime="api_key",
        )
        == "gemini-3.1-flash-tts-preview"
    )
    assert (
        resolve_model_for_runtime(
            "gemini-3.1-flash-tts-preview",
            "tts",
            runtime="vertex",
        )
        == "gemini-3.1-flash-tts-preview"
    )


def test_resolves_gemini_31_flash_image_runtime_names():
    assert (
        resolve_model_for_runtime(
            "gemini-3.1-flash-image-preview",
            "image",
            runtime="api_key",
        )
        == "gemini-3.1-flash-image-preview"
    )
    assert (
        resolve_model_for_runtime(
            "gemini-3.1-flash-image-preview",
            "image",
            runtime="vertex",
        )
        == "gemini-3.1-flash-image-preview"
    )
