import asyncio
import base64
import logging
import mimetypes
import os
from typing import Optional, List, Dict, Any, TYPE_CHECKING

# ✅ Legacy Gemini SDK (as requested)
import google.generativeai as genai
import requests

from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.image.image_model import ImageModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)


def _data_uri(mime_type: str, raw: bytes) -> str:
    """Convert raw bytes to a data URI."""
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _guess_mime_from_url(url: str) -> str:
    """Best-effort MIME guess from URL; fall back to image/jpeg."""
    mime, _ = mimetypes.guess_type(url)
    return mime or "image/jpeg"


def _fetch_image_part(url: str) -> Dict[str, Any]:
    """
    Download an image and return an inline-data Part compatible with the legacy SDK:
    { "mime_type": "...", "data": <bytes> }
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    mime = resp.headers.get("Content-Type") or _guess_mime_from_url(url)
    return {"mime_type": mime.split(";")[0], "data": resp.content}


def _extract_inline_images(response) -> List[Dict[str, bytes]]:
    """
    Collect inline image parts from the legacy SDK response.
    Returns list of { "mime_type": str, "data": bytes }.
    """
    images = []
    try:
        candidates = getattr(response, "candidates", []) or []
        if not candidates:
            return images

        parts = candidates[0].content.parts if candidates[0].content else []
        for p in parts:
            inline = getattr(p, "inline_data", None)
            if not inline:
                continue
            mime = getattr(inline, "mime_type", "") or ""
            if not mime.startswith("image/"):
                continue

            data = getattr(inline, "data", None)
            if isinstance(data, bytes):
                images.append({"mime_type": mime, "data": data})
            elif isinstance(data, str):
                # Some bindings expose base64 text
                images.append({"mime_type": mime, "data": base64.b64decode(data)})
    except Exception as e:
        logger.error("Failed to parse inline image(s): %s", e)
        raise
    return images


class GeminiImageClient(BaseImageClient):
    """
    Image generation client using Google's legacy SDK (`google.generativeai`).

    Notes:
      - We configure `response_mime_type='image/png'` to request image output.
      - You can guide generation with input images by passing URLs; they’re added as inline image Parts.
      - This runs the blocking SDK call in a worker thread to keep your async API.
    """

    def __init__(self, model: "ImageModel", config: "MultimediaConfig"):
        super().__init__(model, config)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Please set the GEMINI_API_KEY environment variable.")

        try:
            genai.configure(api_key=api_key)
            # `self.model.value` should be an image-capable model.
            # Examples (subject to availability): "imagen-3.0-generate", "imagen-3.0-fast",
            # or Gemini image-preview models that support image output.
            model_name = self.model.value or "imagen-3.0-generate"
            self._model = genai.GenerativeModel(model_name)
            logger.info("GeminiImageClient (legacy SDK) initialized for model '%s'.", model_name)
        except Exception as e:
            logger.error("Failed to initialize Gemini image client: %s", e)
            raise RuntimeError(f"Failed to initialize Gemini image client: {e}")

    async def generate_image(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> ImageGenerationResponse:
        """
        Generate an image (text→image or image-guided).

        `generation_config` supports common fields; we always ensure
        `response_mime_type='image/png'` so the SDK returns inline image bytes.
        """
        try:
            logger.info("Generating image with model '%s'...", self._model.model_name)

            # Build contents array: [text, (optional) image parts...]
            contents: List[Any] = [prompt]

            if input_image_urls:
                logger.info("Loading %d input image(s) for guidance...", len(input_image_urls))
                for url in input_image_urls:
                    try:
                        contents.append(_fetch_image_part(url))
                    except Exception as e:
                        logger.error("Skipping image '%s' due to error: %s", url, e)

            # Merge config and force image output
            gen_cfg: Dict[str, Any] = (generation_config or {}).copy()
            gen_cfg["response_mime_type"] = gen_cfg.get("response_mime_type", "image/png")

            # Call the (sync) SDK in a worker thread
            response = await asyncio.to_thread(
                self._model.generate_content,
                contents,
                generation_config=gen_cfg,
            )

            # Handle safety blocks if present
            feedback = getattr(response, "prompt_feedback", None)
            block_reason = getattr(feedback, "block_reason", None)
            if block_reason:
                reason = getattr(block_reason, "name", str(block_reason))
                logger.error("Image generation blocked by safety settings: %s", reason)
                raise ValueError(f"Image generation failed due to safety settings: {reason}")

            images = _extract_inline_images(response)
            if not images:
                logger.warning("No image parts returned for prompt: '%.100s...'", prompt)
                raise ValueError("Gemini API did not return any images.")

            image_urls = [_data_uri(img["mime_type"], img["data"]) for img in images]
            logger.info("Successfully generated %d image(s).", len(image_urls))

            return ImageGenerationResponse(
                image_urls=image_urls,
                revised_prompt=None  # legacy SDK does not provide a revised prompt here
            )

        except Exception as e:
            logger.error("Error during Gemini image generation (legacy SDK): %s", e)
            # Region support / feature gating errors sometimes include 'Unsupported' hints.
            if "Unsupported" in str(e) and "location" in str(e):
                raise ValueError(
                    "Image generation may not be supported in your configured region or project. "
                    "Check your API access and region settings."
                )
            raise ValueError(f"Google Gemini image generation failed: {str(e)}")

    async def edit_image(
        self,
        prompt: str,
        input_image_urls: List[str],
        mask_url: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> ImageGenerationResponse:
        """
        Image editing/redraw with masks isn’t exposed via this legacy path here.
        """
        logger.error("Image editing is not supported by the GeminiImageClient (legacy SDK).")
        raise NotImplementedError("The GeminiImageClient does not support the edit_image method.")

    async def cleanup(self):
        logger.debug("GeminiImageClient cleanup called (legacy SDK; nothing to release).")
