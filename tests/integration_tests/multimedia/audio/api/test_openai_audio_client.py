import logging
import os
from pathlib import Path

import pytest

from autobyteus.multimedia import SpeechGenerationResponse
from autobyteus.multimedia.audio import audio_client_factory

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def set_openai_env():
    """Skips tests if the OpenAI API key is not available."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set. Skipping OpenAI audio tests.")


@pytest.fixture
def openai_tts_client(set_openai_env):
    """Provides a gpt-4o-mini-tts client from the factory."""
    return audio_client_factory.create_audio_client("gpt-4o-mini-tts")


def _cleanup_audio_file(audio_path: Path):
    try:
        if audio_path.exists():
            audio_path.unlink()
    except OSError as exc:
        logger.error("Failed to remove test audio file %s: %s", audio_path, exc)


@pytest.mark.asyncio
async def test_openai_generate_speech_default(openai_tts_client):
    """Tests speech generation with default OpenAI TTS settings."""
    prompt = "Hello from the OpenAI TTS integration test."
    response = await openai_tts_client.generate_speech(prompt)

    assert isinstance(response, SpeechGenerationResponse)
    assert isinstance(response.audio_urls, list)
    assert response.audio_urls

    audio_path = Path(response.audio_urls[0])
    assert audio_path.exists()
    assert audio_path.is_file()
    assert audio_path.suffix == ".mp3"

    _cleanup_audio_file(audio_path)


@pytest.mark.asyncio
async def test_openai_generate_speech_with_overrides(openai_tts_client):
    """Tests speech generation with custom voice and format overrides."""
    prompt = "Please read this line slowly using a different voice."
    generation_config = {"voice": "ash", "format": "wav", "instructions": "Slow pace, friendly tone."}
    response = await openai_tts_client.generate_speech(prompt, generation_config=generation_config)

    assert isinstance(response, SpeechGenerationResponse)
    assert response.audio_urls

    audio_path = Path(response.audio_urls[0])
    assert audio_path.exists()
    assert audio_path.is_file()
    assert audio_path.suffix == ".wav"

    _cleanup_audio_file(audio_path)
