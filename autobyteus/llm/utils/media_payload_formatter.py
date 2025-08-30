import base64
import mimetypes
from typing import Dict, Union
from pathlib import Path
import httpx
import logging

logger = logging.getLogger(__name__)

# FIX: Instantiate the client with verify=False to allow for self-signed certificates
# in local development environments, which is a common use case.
_http_client = httpx.AsyncClient(verify=False)

# Add a prominent security warning to inform developers about the disabled SSL verification.
logger.warning(
    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
    "SECURITY WARNING: SSL certificate verification is DISABLED for the image "
    "downloader (httpx client in media_payload_formatter.py).\n"
    "This is intended for development and testing with local servers using "
    "self-signed certificates. In a production environment, this could expose "
    "the system to Man-in-the-Middle (MitM) attacks when downloading images from "
    "the public internet.\n"
    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
)


def get_mime_type(file_path: str) -> str:
    """Determine MIME type of file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith('image/'):
        return 'image/jpeg'  # default fallback
    return mime_type


def is_base64(s: str) -> bool:
    """Check if a string is a valid base64 encoded string."""
    try:
        # Check if the string has valid base64 characters and padding
        if not isinstance(s, str) or len(s) % 4 != 0:
            return False
        base64.b64decode(s, validate=True)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_image_path(path: str) -> bool:
    """Check if path exists and has a valid image extension."""
    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    try:
        file_path = Path(path)
        return file_path.is_file() and file_path.suffix.lower() in valid_extensions
    except (TypeError, ValueError):
        return False


def create_data_uri(mime_type: str, base64_data: str) -> Dict:
    """Create properly structured data URI object for API."""
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_data}"
        }
    }

def file_to_base64(path: str) -> str:
    """Reads an image file from a local path and returns it as a base64 encoded string."""
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to read and encode image file at {path}: {e}")
        raise

async def url_to_base64(url: str) -> str:
    """Downloads an image from a URL and returns it as a base64 encoded string."""
    try:
        response = await _http_client.get(url)
        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
    except httpx.HTTPError as e:
        logger.error(f"Failed to download image from URL {url}: {e}")
        raise

async def image_source_to_base64(image_source: str) -> str:
    """
    Orchestrator function that converts an image source (file path, URL, or existing base64)
    into a base64 encoded string by delegating to specialized functions.
    """
    if is_valid_image_path(image_source):
        return file_to_base64(image_source)
    
    if image_source.startswith(("http://", "https://")):
        return await url_to_base64(image_source)

    if is_base64(image_source):
        return image_source

    raise ValueError(f"Invalid image source: not a valid file path, URL, or base64 string.")
