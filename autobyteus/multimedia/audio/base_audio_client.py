from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from autobyteus.multimedia.utils.response_types import SpeechGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.audio.audio_model import AudioModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig


class BaseAudioClient(ABC):
    """
    Abstract base class for audio clients that connect to models for audio generation.
    """
    def __init__(self, model: "AudioModel", config: "MultimediaConfig"):
        self.model = model
        self.config = config

    @abstractmethod
    async def generate_speech(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpeechGenerationResponse:
        """
        Generates spoken audio from text (Text-to-Speech).

        Args:
            prompt (str): The text to be converted to speech.
            generation_config (Optional[Dict[str, Any]]): Provider-specific parameters
                                                        (e.g., voice_name, speaker_mapping).
            **kwargs: Additional keyword arguments for extensibility.

        Returns:
            SpeechGenerationResponse: An object containing URLs or paths to the generated audio files.
        """
        pass

    async def cleanup(self):
        """Optional cleanup method for resources like network clients."""
        pass
