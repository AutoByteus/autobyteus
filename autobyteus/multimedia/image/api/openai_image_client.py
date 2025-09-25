import logging
import os
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from openai import OpenAI
from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.image.image_model import ImageModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)

class OpenAIImageClient(BaseImageClient):
    """
    An image client that uses OpenAI's DALL-E models.
    """

    def __init__(self, model: "ImageModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set.")
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        self.client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
        logger.info(f"OpenAIImageClient initialized for model '{self.model.name}'.")

    async def generate_image(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Generates an image using an OpenAI DALL-E model via the v1/images/generations endpoint.
        Note: This endpoint does not support image inputs, even for multimodal models like gpt-image-1.
        """
        if input_image_urls:
            logger.warning(
                f"The OpenAI `images.generate` API used by this client does not support input images. "
                f"The images provided for model '{self.model.value}' will be ignored. "
                f"To use image inputs, a client based on the Chat Completions API is required."
            )

        try:
            image_model = self.model.value
            logger.info(f"Generating image with OpenAI model '{image_model}' and prompt: '{prompt[:50]}...'")

            # Combine default config with any overrides
            final_config = self.config.to_dict().copy()
            if generation_config:
                final_config.update(generation_config)

            response = self.client.images.generate(
                model=image_model,
                prompt=prompt,
                n=final_config.get("n", 1),
                size=final_config.get("size", "1024x1024"),
                quality=final_config.get("quality", "standard"),
                style=final_config.get("style", "vivid"),
                response_format="url"
            )

            image_urls_list: List[str] = [img.url for img in response.data if img.url]
            revised_prompt: Optional[str] = response.data[0].revised_prompt if response.data and hasattr(response.data[0], 'revised_prompt') else None

            if not image_urls_list:
                raise ValueError("OpenAI API did not return any image URLs.")

            logger.info(f"Successfully generated {len(image_urls_list)} image(s).")

            return ImageGenerationResponse(
                image_urls=image_urls_list,
                revised_prompt=revised_prompt
            )
        except Exception as e:
            logger.error(f"Error during OpenAI image generation: {str(e)}")
            raise ValueError(f"OpenAI image generation failed: {str(e)}")

    async def edit_image(
        self,
        prompt: str,
        input_image_urls: List[str],
        mask_url: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Edits an image using an OpenAI model that supports the v1/images/edits endpoint.
        """
        if not input_image_urls:
            raise ValueError("At least one input image URL must be provided for editing.")

        source_image_url = input_image_urls[0]
        if len(input_image_urls) > 1:
            logger.warning(f"OpenAI edit endpoint only supports one input image. Using '{source_image_url}' and ignoring the rest.")

        try:
            logger.info(f"Editing image '{source_image_url}' with prompt: '{prompt[:50]}...'")

            # Combine default config with any overrides
            final_config = self.config.to_dict().copy()
            if generation_config:
                final_config.update(generation_config)

            with open(source_image_url, "rb") as image_file:
                mask_file = open(mask_url, "rb") if mask_url else None
                try:
                    response = self.client.images.edit(
                        image=image_file,
                        mask=mask_file,
                        prompt=prompt,
                        model=self.model.value,
                        n=final_config.get("n", 1),
                        size=final_config.get("size", "1024x1024"),
                        response_format="url"
                    )
                finally:
                    if mask_file:
                        mask_file.close()

            image_urls_list: List[str] = [img.url for img in response.data if img.url]
            if not image_urls_list:
                raise ValueError("OpenAI API did not return any edited image URLs.")

            logger.info(f"Successfully edited image, generated {len(image_urls_list)} version(s).")
            return ImageGenerationResponse(image_urls=image_urls_list)

        except FileNotFoundError as e:
            logger.error(f"Image file not found for editing: {e.filename}")
            raise
        except Exception as e:
            logger.error(f"Error during OpenAI image editing: {str(e)}")
            # The API might return a 400 Bad Request if the model doesn't support edits
            if "does not support image editing" in str(e):
                raise ValueError(f"The model '{self.model.value}' does not support the image editing endpoint.")
            raise ValueError(f"OpenAI image editing failed: {str(e)}")


    async def cleanup(self):
        # The OpenAI client does not require explicit cleanup of a session.
        logger.debug("OpenAIImageClient cleanup called.")
