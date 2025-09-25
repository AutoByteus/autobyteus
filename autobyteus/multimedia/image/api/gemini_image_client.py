import logging
import base64
import os
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from google import genai
from PIL import Image
import requests

from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse
from autobyteus.multimedia.utils.api_utils import load_image_from_url

if TYPE_CHECKING:
    from autobyteus.multimedia.image.image_model import ImageModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)

class GeminiImageClient(BaseImageClient):
    """
    An image client that uses Google's Gemini models for image generation tasks.

    **Setup Requirements:**
    1.  **Authentication:** Set the `GEMINI_API_KEY` environment variable with your API key.
    """

    def __init__(self, model: "ImageModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Please set the GEMINI_API_KEY environment variable.")
        
        try:
            self.client = genai.Client()
            self.async_client = self.client.aio
            logger.info(f"GeminiImageClient initialized for model '{self.model.name}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client for images: {e}")
            raise RuntimeError(f"Failed to initialize Gemini client for images: {e}")

    async def generate_image(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Generates an image using a Google Gemini model. Can be text-to-image or image-to-image.
        """
        try:
            logger.info(f"Generating image with Google Gemini model '{self.model.value}'...")

            content = [prompt]
            if input_image_urls:
                logger.info(f"Loading {len(input_image_urls)} input image(s) for generation.")
                for url in input_image_urls:
                    try:
                        content.append(load_image_from_url(url))
                    except Exception as e:
                        logger.error(f"Skipping image at '{url}' due to loading error: {e}")

            # Note: The google-genai library uses the synchronous client for the `.generate_content` method on a model
            # even in an async context, as there isn't a direct async equivalent exposed for this specific call on the model object.
            # We use the top-level async client for other potential future calls if the library API changes.
            model_instance = self.client.get_generative_model(model_name=f"models/{self.model.value}")
            response = await model_instance.generate_content_async(contents=content)


            image_urls = []
            for part in response.parts:
                if part.inline_data and "image" in part.inline_data.mime_type:
                    image_bytes = part.inline_data.data
                    base64_image = base64.b64encode(image_bytes).decode("utf-8")
                    data_uri = f"data:{part.inline_data.mime_type};base64,{base64_image}"
                    image_urls.append(data_uri)
            
            if not image_urls:
                # Check for a safety-related refusal to generate content
                if response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name
                    logger.error(f"Image generation blocked due to safety settings. Reason: {reason}")
                    raise ValueError(f"Image generation failed due to safety settings: {reason}")
                
                logger.warning(f"Gemini API did not return any images for the prompt: '{prompt[:100]}...'")
                raise ValueError("Gemini API did not return any processable images.")

            logger.info(f"Successfully generated {len(image_urls)} image(s) with Gemini.")

            return ImageGenerationResponse(
                image_urls=image_urls,
                revised_prompt=None  # genai library does not provide a revised prompt for images
            )
        except Exception as e:
            logger.error(f"Error during Google Gemini image generation: {str(e)}")
            # Re-raise with a more specific message if it's a known type of error
            if "Unsupported" in str(e) and "location" in str(e):
                 raise ValueError(f"Image generation is not supported in your configured region. Please check your Google Cloud project settings.")
            raise ValueError(f"Google Gemini image generation failed: {str(e)}")

    async def edit_image(
        self,
        prompt: str,
        input_image_urls: List[str],
        mask_url: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Edits an image using a Google Gemini model by providing the image(s) as context.
        This method leverages the same underlying 'generate_content' call as generate_image.
        Note: The Gemini API via the google-genai library does not support explicit masking.
        """
        if mask_url:
            logger.warning(
                f"The GeminiImageClient for model '{self.model.name}' received a 'mask_url' but does not support "
                "explicit masking. The mask will be ignored. The model will perform a general edit based on the prompt."
            )
        
        # For Gemini, editing is the same as generating with an input image.
        # The generate_image method already handles this logic correctly.
        return await self.generate_image(
            prompt=prompt,
            input_image_urls=input_image_urls,
            generation_config=generation_config,
            **kwargs
        )

    async def cleanup(self):
        logger.debug("GeminiImageClient cleanup called.")
