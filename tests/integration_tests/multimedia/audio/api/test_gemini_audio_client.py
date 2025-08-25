import pytest
import os
import logging
from pathlib import Path

from autobyteus.multimedia import SpeechGenerationResponse
from autobyteus.multimedia.audio import audio_client_factory

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def set_gemini_env():
    """Skips tests if the Gemini API key is not set."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY environment variable not set. Skipping Gemini audio tests.")

@pytest.fixture
def tts_client(set_gemini_env):
    """Provides a gemini-2.5-flash-tts client from the factory."""
    return audio_client_factory.create_audio_client("gemini-2.5-flash-tts")

@pytest.mark.asyncio
async def test_gemini_generate_speech(tts_client):
    """Tests successful speech generation with a gemini TTS model."""
    prompt = "Hello world from the integration test."
    response = await tts_client.generate_speech(prompt)

    assert isinstance(response, SpeechGenerationResponse)
    assert isinstance(response.audio_urls, list)
    assert len(response.audio_urls) > 0
    
    audio_path = Path(response.audio_urls[0])
    assert audio_path.exists()
    assert audio_path.is_file()
    assert audio_path.suffix == ".wav"
    
    # Cleanup
    try:
        os.remove(audio_path)
    except OSError as e:
        logger.error(f"Error removing test audio file {audio_path}: {e}")
