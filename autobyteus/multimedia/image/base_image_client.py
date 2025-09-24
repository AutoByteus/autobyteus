from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.image.image_model import ImageModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig


class BaseImageClient(ABC):
    """
    Abstract base class for image clients that connect to models for image generation and editing.
    """
    def __init__(self, model: "ImageModel", config: "MultimediaConfig"):
        self.model = model
        self.config = config

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Generates an image based on a textual prompt.

        Args:
            prompt (str): The text prompt describing the image to generate.
            input_image_urls (Optional[List[str]]): A list of URLs or local paths to input images
                                                    for image-to-image generation.
            generation_config (Optional[Dict[str, Any]]): Provider-specific parameters for image generation
                                                        to override defaults.
                                                        (e.g., n, size, quality, style).
            **kwargs: Additional keyword arguments for extensibility.

        Returns:
            ImageGenerationResponse: An object containing URLs to the generated images.
        """
        pass

    @abstractmethod
    async def edit_image(
        self,
        prompt: str,
        input_image_urls: List[str],
        mask_url: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Edits an existing image based on a textual prompt.

        Args:
            prompt (str): A text prompt describing the desired edits.
            input_image_urls (List[str]): The path(s) or URL(s) to the source image(s) to edit.
            mask_url (Optional[str]): The path to a mask image. The transparent areas of the mask
                                       indicate where the image should be edited.
            generation_config (Optional[Dict[str, Any]]): Provider-specific parameters.
            **kwargs: Additional keyword arguments for extensibility.

        Returns:
            ImageGenerationResponse: An object containing URLs to the edited images.
        """
        pass

    async def cleanup(self):
        """Optional cleanup method for resources like network clients."""
        pass
