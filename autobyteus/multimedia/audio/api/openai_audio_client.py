import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING

from openai import OpenAI

from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.multimedia.utils.response_types import SpeechGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.audio.audio_model import AudioModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)

_AUDIO_TEMP_DIR = Path("/tmp/autobyteus_audio")


def _save_audio_bytes(audio_bytes: bytes, file_extension: Optional[str]) -> str:
    """Saves audio bytes to disk with a random file name."""
    _AUDIO_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    suffix = (file_extension or "mp3").lstrip(".")
    file_path = _AUDIO_TEMP_DIR / f"{uuid.uuid4()}.{suffix}"
    file_path.write_bytes(audio_bytes)
    logger.info(f"Successfully saved generated audio to {file_path}")
    return str(file_path)


class OpenAIAudioClient(BaseAudioClient):
    """
    An audio client that uses OpenAI's Text-to-Speech (Speech) API.

    **Setup Requirements:**
    1. Set the `OPENAI_API_KEY` environment variable with your OpenAI API key.
    """

    def __init__(self, model: "AudioModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set.")
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        try:
            self.client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
            logger.info(f"OpenAIAudioClient initialized for model '{self.model.name}'.")
        except Exception as exc:
            logger.error(f"Failed to configure OpenAI client: {exc}")
            raise RuntimeError(f"Failed to configure OpenAI client: {exc}") from exc

    async def generate_speech(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpeechGenerationResponse:
        """
        Generates speech using OpenAI's Speech endpoint and returns a local file path.
        """
        try:
            final_config = self.config.to_dict().copy()
            if generation_config:
                final_config.update(generation_config)

            voice = final_config.get("voice", "alloy")
            response_format = (
                final_config.get("response_format")
                or final_config.get("format")
                or "mp3"
            )
            instructions = final_config.get("instructions")

            logger.info(
                "Generating speech with OpenAI TTS model '%s' using voice '%s' and format '%s'.",
                self.model.value,
                voice,
                response_format,
            )

            request_kwargs = {
                "model": self.model.value,
                "voice": voice,
                "input": prompt,
            }

            if instructions:
                request_kwargs["instructions"] = instructions

            if response_format:
                request_kwargs["response_format"] = response_format

            response = await asyncio.to_thread(
                self.client.audio.speech.create,
                **request_kwargs,
            )

            audio_bytes = getattr(response, "content", None)
            if not audio_bytes:
                raise ValueError("OpenAI Speech API returned an empty response.")

            audio_path = _save_audio_bytes(audio_bytes, response_format)
            return SpeechGenerationResponse(audio_urls=[audio_path])

        except Exception as exc:
            logger.error("Error during OpenAI speech generation: %s", exc)
            raise ValueError(f"OpenAI speech generation failed: {exc}") from exc

    async def cleanup(self):
        logger.debug("OpenAIAudioClient cleanup called.")
