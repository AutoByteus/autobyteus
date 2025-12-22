import logging
import base64
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from google.genai import types as genai_types

from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse
from autobyteus.multimedia.utils.api_utils import load_image_from_url
from autobyteus.utils.gemini_helper import initialize_gemini_client_with_runtime
from autobyteus.utils.gemini_model_mapping import resolve_model_for_runtime

if TYPE_CHECKING:
    from autobyteus.multimedia.image.image_model import ImageModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)

class GeminiImageClient(BaseImageClient):
    """
    An image client that uses Google's Gemini models for image generation tasks.

    **Setup Requirements:**
    1.  **AI Studio Mode:** Set `GEMINI_API_KEY`.
    2.  **Vertex AI Mode:** Set `VERTEX_AI_PROJECT` and `VERTEX_AI_LOCATION`.
    """

    def __init__(self, model: "ImageModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        
        try:
            self.client, self.runtime_info = initialize_gemini_client_with_runtime()
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

            config_dict: Dict[str, Any] = {}
            if self.config and self.config.params:
                config_dict.update(self.config.params)
            if generation_config:
                config_dict.update(generation_config)
            if "response_modalities" not in config_dict:
                if getattr(self, "runtime_info", None) and self.runtime_info.runtime == "vertex":
                    config_dict["response_modalities"] = ["TEXT", "IMAGE"]
                else:
                    config_dict["response_modalities"] = ["IMAGE"]
            config = genai_types.GenerateContentConfig(**config_dict)
            
            # FIX: Removed 'models/' prefix from model_name to support Vertex AI
            runtime_adjusted_model = resolve_model_for_runtime(
                self.model.value,
                modality="image",
                runtime=getattr(self, "runtime_info", None) and self.runtime_info.runtime,
            )
            if runtime_adjusted_model != self.model.value:
                logger.info(
                    "Using runtime-adjusted Gemini image model '%s' (requested '%s').",
                    runtime_adjusted_model,
                    self.model.value,
                )
            response = await self.async_client.models.generate_content(
                model=runtime_adjusted_model,
                contents=content,
                config=config,
            )


            image_urls = []
            for part in response.parts or []:
                if part.inline_data and part.inline_data.mime_type and "image" in part.inline_data.mime_type:
                    image_bytes = part.inline_data.data
                    base64_image = base64.b64encode(image_bytes).decode("utf-8")
                    data_uri = f"data:{part.inline_data.mime_type};base64,{base64_image}"
                    image_urls.append(data_uri)
            
            if not image_urls:
                # Check for a safety-related refusal to generate content
                if response.prompt_feedback and response.prompt_feedback.block_reason:
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
