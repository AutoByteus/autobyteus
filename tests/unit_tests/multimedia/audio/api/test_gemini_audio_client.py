from types import SimpleNamespace

import pytest

from autobyteus.multimedia.audio.api import gemini_audio_client as gemini_audio_module
from autobyteus.multimedia.audio.api.gemini_audio_client import GeminiAudioClient
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _DummyModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        inline_data = SimpleNamespace(data=b"\x00\x01\x02\x03", mime_type="audio/l16;rate=24000")
        part = SimpleNamespace(inline_data=inline_data)
        content = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        return SimpleNamespace(candidates=[candidate])


class _DummyClient:
    def __init__(self):
        self.models = _DummyModels()
        self.aio = None


def _build_client(monkeypatch, tmp_path, *, params=None):
    dummy_client = _DummyClient()
    monkeypatch.setattr(
        gemini_audio_module,
        "initialize_gemini_client_with_runtime",
        lambda: (dummy_client, SimpleNamespace(runtime="api_key")),
    )
    monkeypatch.setattr(gemini_audio_module, "_AUDIO_TEMP_DIR", str(tmp_path))
    model = SimpleNamespace(name="gemini-3.1-flash-tts", value="gemini-3.1-flash-tts-preview")
    client = GeminiAudioClient(model=model, config=MultimediaConfig(params=params or {}))
    return client, dummy_client


@pytest.mark.anyio
async def test_gemini_tts_passes_language_code_for_single_speaker(monkeypatch, tmp_path):
    client, dummy_client = _build_client(monkeypatch, tmp_path, params={"voice_name": "Kore"})

    await client.generate_speech(
        "Say hello.",
        generation_config={
            "language_code": "en-US",
            "style_instructions": "Warm, measured delivery with a light smile.",
        },
    )

    call = dummy_client.models.calls[0]
    assert "### DIRECTOR'S NOTES" in call["contents"]
    assert "### TRANSCRIPT" in call["contents"]

    speech_config = call["config"].speech_config
    assert speech_config.language_code == "en-US"
    assert speech_config.voice_config.prebuilt_voice_config.voice_name == "Kore"


@pytest.mark.anyio
async def test_gemini_tts_passes_language_code_for_multi_speaker(monkeypatch, tmp_path):
    client, dummy_client = _build_client(monkeypatch, tmp_path)

    await client.generate_speech(
        "Joe: Hello.\nJane: Hi.",
        generation_config={
            "mode": "multi-speaker",
            "language_code": "en-US",
            "speaker_mapping": [
                {"speaker": "Joe", "voice": "Puck"},
                {"speaker": "Jane", "voice": "Kore"},
            ],
        },
    )

    speech_config = dummy_client.models.calls[0]["config"].speech_config
    assert speech_config.language_code == "en-US"
    speaker_voice_configs = speech_config.multi_speaker_voice_config.speaker_voice_configs
    assert [speaker.speaker for speaker in speaker_voice_configs] == ["Joe", "Jane"]
    assert speaker_voice_configs[0].voice_config.prebuilt_voice_config.voice_name == "Puck"


@pytest.mark.anyio
async def test_gemini_tts_rejects_more_than_two_speakers(monkeypatch, tmp_path):
    client, _dummy_client = _build_client(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="up to 2 distinct speakers"):
        await client.generate_speech(
            "A: One.\nB: Two.\nC: Three.",
            generation_config={
                "mode": "multi-speaker",
                "speaker_mapping": [
                    {"speaker": "A", "voice": "Puck"},
                    {"speaker": "B", "voice": "Kore"},
                    {"speaker": "C", "voice": "Zephyr"},
                ],
            },
        )
