import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from openai import OpenAI

from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse
from autobyteus.utils.download_utils import download_file_from_url

if TYPE_CHECKING:
    from autobyteus.multimedia.image.image_model import ImageModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)


def _mime_type_from_format(output_format: str) -> str:
    fmt = (output_format or "png").lower()
    if fmt in {"jpg", "jpeg"}:
        return "image/jpeg"
    if fmt == "webp":
        return "image/webp"
    return "image/png"


class OpenAIImageClient(BaseImageClient):
    """
    An image client that uses OpenAI's gpt-image series via the images API.
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
        Generates an image using OpenAI's images generation endpoint.
        Note: This endpoint does not support image inputs.
        """
        if input_image_urls:
            logger.warning(
                "The OpenAI `images.generate` API used by this client does not support input images. "
                "The images provided for model '%s' will be ignored. "
                "To use image inputs, a client based on the Chat Completions API is required.",
                self.model.value,
            )

        try:
            image_model = self.model.value
            logger.info("Generating image with OpenAI model '%s' and prompt: '%s...'", image_model, prompt[:50])

            # Combine default config with any overrides
            final_config = self.config.to_dict().copy()
            if generation_config:
                final_config.update(generation_config)
            # Always request a single image for simplicity
            final_config["n"] = 1

            request_kwargs = {
                "model": image_model,
                "prompt": prompt,
                "n": 1,
                "size": final_config.get("size", "1024x1024"),
                "quality": final_config.get("quality", "standard"),
            }
            if "output_format" in final_config:
                request_kwargs["output_format"] = final_config["output_format"]
            if "output_compression" in final_config:
                request_kwargs["output_compression"] = final_config["output_compression"]

            response = self.client.images.generate(**request_kwargs)

            output_format = final_config.get("output_format", "png")
            mime_type = _mime_type_from_format(output_format)
            image_urls_list: List[str] = []
            for img in response.data:
                if getattr(img, "url", None):
                    image_urls_list.append(img.url)
                elif getattr(img, "b64_json", None):
                    image_urls_list.append(f"data:{mime_type};base64,{img.b64_json}")

            revised_prompt: Optional[str] = (
                response.data[0].revised_prompt
                if response.data and hasattr(response.data[0], "revised_prompt")
                else None
            )

            if not image_urls_list:
                raise ValueError("OpenAI API did not return any image data.")

            logger.info("Successfully generated %s image(s).", len(image_urls_list))

            return ImageGenerationResponse(
                image_urls=image_urls_list,
                revised_prompt=revised_prompt
            )
        except Exception as e:
            logger.error("Error during OpenAI image generation: %s", str(e))
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
            logger.warning(
                "OpenAI edit endpoint only supports one input image. Using '%s' and ignoring the rest.",
                source_image_url,
            )

        temp_image_path: Optional[Path] = None
        temp_mask_path: Optional[Path] = None
        try:
            logger.info("Editing image '%s' with prompt: '%s...'", source_image_url, prompt[:50])

            # Combine default config with any overrides
            final_config = self.config.to_dict().copy()
            if generation_config:
                final_config.update(generation_config)
            # Always request a single edited image
            final_config["n"] = 1

            source_path = Path(source_image_url)
            if not source_path.exists():
                temp_image_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                temp_image_file.close()
                temp_image_path = Path(temp_image_file.name)
                await download_file_from_url(source_image_url, temp_image_path)
                source_path = temp_image_path

            if mask_url:
                mask_path = Path(mask_url)
                if not mask_path.exists():
                    temp_mask_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    temp_mask_file.close()
                    temp_mask_path = Path(temp_mask_file.name)
                    await download_file_from_url(mask_url, temp_mask_path)
                    mask_path = temp_mask_path
            else:
                mask_path = None

            with open(source_path, "rb") as image_file:
                mask_file = open(mask_path, "rb") if mask_path else None
                try:
                    request_kwargs = {
                        "image": image_file,
                        "prompt": prompt,
                        "model": self.model.value,
                        "n": final_config.get("n", 1),
                        "size": final_config.get("size", "1024x1024"),
                    }
                    if mask_file:
                        request_kwargs["mask"] = mask_file
                    if "output_format" in final_config:
                        request_kwargs["output_format"] = final_config["output_format"]
                    if "output_compression" in final_config:
                        request_kwargs["output_compression"] = final_config["output_compression"]
                    response = self.client.images.edit(**request_kwargs)
                finally:
                    if mask_file:
                        mask_file.close()

            output_format = final_config.get("output_format", "png")
            mime_type = _mime_type_from_format(output_format)
            image_urls_list: List[str] = []
            for img in response.data:
                if getattr(img, "url", None):
                    image_urls_list.append(img.url)
                elif getattr(img, "b64_json", None):
                    image_urls_list.append(f"data:{mime_type};base64,{img.b64_json}")

            if not image_urls_list:
                raise ValueError("OpenAI API did not return any edited image data.")

            logger.info("Successfully edited image, generated %s version(s).", len(image_urls_list))
            return ImageGenerationResponse(image_urls=image_urls_list)

        except FileNotFoundError as e:
            logger.error("Image file not found for editing: %s", e.filename)
            raise
        except Exception as e:
            logger.error("Error during OpenAI image editing: %s", str(e))
            if "does not support image editing" in str(e):
                raise ValueError(f"The model '{self.model.value}' does not support the image editing endpoint.")
            raise ValueError(f"OpenAI image editing failed: {str(e)}")
        finally:
            if temp_image_path and temp_image_path.exists():
                try:
                    temp_image_path.unlink()
                except OSError:
                    logger.warning("Failed to clean up temp image file: %s", temp_image_path)
            if temp_mask_path and temp_mask_path.exists():
                try:
                    temp_mask_path.unlink()
                except OSError:
                    logger.warning("Failed to clean up temp mask file: %s", temp_mask_path)

    async def cleanup(self):
        # The OpenAI client does not require explicit cleanup of a session.
        logger.debug("OpenAIImageClient cleanup called.")
