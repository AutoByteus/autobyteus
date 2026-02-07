import base64
import mimetypes
from typing import Dict
from pathlib import Path
import httpx
import logging
from urllib.parse import urlparse

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
    if not mime_type:
        return 'application/octet-stream'  # generic fallback
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


def is_valid_media_path(path: str) -> bool:
    """Check if path exists and has a valid media extension."""
    valid_extensions = {
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        # Audio
        ".mp3", ".wav", ".ogg", ".aac", ".flac",
        # Video
        ".mp4", ".mpeg", ".mov", ".avi", ".webm", ".mkv"
    }
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


def is_data_uri(value: str) -> bool:
    """Checks whether the value is already a data URI."""
    return isinstance(value, str) and value.startswith("data:")


def _is_existing_file_path(path: str) -> bool:
    try:
        return Path(path).is_file()
    except (TypeError, ValueError):
        return False


def file_to_base64(path: str) -> str:
    """Reads a file from a local path and returns it as a base64 encoded string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to read and encode file at {path}: {e}")
        raise

async def url_to_base64(url: str) -> str:
    """Downloads content from a URL and returns it as a base64 encoded string."""
    try:
        response = await _http_client.get(url)
        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
    except httpx.HTTPError as e:
        logger.error(f"Failed to download from URL {url}: {e}")
        raise

async def media_source_to_base64(media_source: str) -> str:
    """
    Orchestrator function that converts a media source (file path, URL, or existing base64)
    into a base64 encoded string by delegating to specialized functions.
    """
    if is_valid_media_path(media_source):
        return file_to_base64(media_source)
    
    if media_source.startswith(("http://", "https://")):
        return await url_to_base64(media_source)

    if is_base64(media_source):
        return media_source

    raise ValueError(f"Invalid media source: not a valid file path, URL, or base64 string.")


async def media_source_to_data_uri(media_source: str) -> str:
    """
    Converts a media source (data URI, local path, URL, or raw base64)
    into a data URI string.
    """
    if is_data_uri(media_source):
        return media_source

    if media_source.startswith(("http://", "https://")):
        try:
            response = await _http_client.get(media_source)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to convert URL to data URI {media_source}: {e}")
            raise

        header_content_type = response.headers.get("content-type", "")
        mime_type_from_header = header_content_type.split(";")[0].strip() if header_content_type else ""
        parsed_path = urlparse(media_source).path
        mime_type_from_path = get_mime_type(parsed_path)
        mime_type = mime_type_from_header or mime_type_from_path or "application/octet-stream"
        base64_data = base64.b64encode(response.content).decode("utf-8")
        return f"data:{mime_type};base64,{base64_data}"

    if _is_existing_file_path(media_source):
        base64_data = file_to_base64(media_source)
        mime_type = get_mime_type(media_source)
        return f"data:{mime_type};base64,{base64_data}"

    if is_base64(media_source):
        return f"data:application/octet-stream;base64,{media_source}"

    raise ValueError(
        "Invalid media source: not a valid file path, URL, base64 string, or data URI."
    )
