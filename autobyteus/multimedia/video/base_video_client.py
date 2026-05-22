from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from autobyteus.multimedia.utils.response_types import VideoGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.video.video_model import VideoModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig


class BaseVideoClient(ABC):
    """
    Abstract base class for video generation clients.
    """
    def __init__(self, model: "VideoModel", config: "MultimediaConfig"):
        self.model = model
        self.config = config

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        input_audio_urls: Optional[List[str]] = None,
        input_video_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> VideoGenerationResponse:
        """
        Generates a video from a text prompt and optional media references.
        """
        pass

    async def cleanup(self):
        """Optional cleanup method for resources like network clients."""
        pass
