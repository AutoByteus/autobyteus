import logging
import os
import base64
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import google.generativeai as genai
from PIL import Image
import requests
from io import BytesIO
import mimetypes


from autobyteus.multimedia.base_multimedia_client import BaseMultimediaClient
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.models import MultimediaModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)


def _load_image_from_url(url: str) -> Image.Image:
    """Loads an image from a URL (http, https, or file path)."""
    try:
        if url.startswith(('http://', 'https://')):
            response = requests.get(url, stream=True)
            response.raise_for_status()
            return Image.open(response.raw)
        else:
            # Assume it's a local file path
            return Image.open(url)
    except Exception as e:
        logger.error(f"Failed to load image from URL/path '{url}': {e}")
        raise


class GeminiMultimediaClient(BaseMultimediaClient):
    """
    A multimedia client that uses Google's Gemini models (which can invoke Imagen)
    via the `google-generativeai` library.

    **Setup Requirements:**
    1.  **Authentication:** Set the `GEMINI_API_KEY` environment variable with your API key.
    """

    def __init__(self, model: "MultimediaModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Please set the GEMINI_API_KEY environment variable.")

        try:
            genai.configure(api_key=api_key)
            logger.info(f"GeminiMultimediaClient initialized for model '{self.model.name}'.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            raise RuntimeError(f"Failed to configure Gemini client: {e}")

    async def generate_image(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> ImageGenerationResponse:
        """
        Generates an image using a Google Gemini model. Can be text-to-image or image-to-image.
        """
        model_name = self.model.value
        
        try:
            logger.info(f"Generating image with Google Gemini model '{model_name}'...")
            model = genai.GenerativeModel(model_name)

            content = [prompt]
            if input_image_urls:
                logger.info(f"Loading {len(input_image_urls)} input image(s) for generation.")
                for url in input_image_urls:
                    try:
                        content.append(_load_image_from_url(url))
                    except Exception as e:
                        logger.error(f"Skipping image at '{url}' due to loading error: {e}")

            response = await model.generate_content_async(content)

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
        generation_config: Optional[Dict[str, Any]] = None
    ) -> ImageGenerationResponse:
        """
        Image editing is not currently supported via this Gemini implementation.
        """
        logger.error("Image editing is not supported by the GeminiMultimediaClient at this time.")
        raise NotImplementedError("The GeminiMultimediaClient does not support the edit_image method.")

    async def cleanup(self):
        logger.debug("GeminiMultimediaClient cleanup called.")
