import logging
from PIL import Image
import requests

logger = logging.getLogger(__name__)

def load_image_from_url(url: str) -> Image.Image:
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
