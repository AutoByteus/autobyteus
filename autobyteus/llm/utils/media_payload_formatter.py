import base64
import mimetypes
from typing import Dict, Union
from pathlib import Path


def get_mime_type(file_path: str) -> str:
    """Determine MIME type of file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith('image/'):
        return 'image/jpeg'  # default fallback
    return mime_type


def is_base64(s: str) -> bool:
    """Check if a string is base64 encoded."""
    try:
        base64.b64decode(s)
        return True
    except Exception:
        return False


def is_valid_image_path(path: str) -> bool:
    """Check if path exists and has a valid image extension."""
    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_path = Path(path)
    return file_path.exists() and file_path.suffix.lower() in valid_extensions


def create_data_uri(mime_type: str, base64_data: str) -> Dict:
    """Create properly structured data URI object for API."""
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_data}"
        }
    }


def process_image(image_url: Union[str, bytes]) -> Dict:
    """
    Process image input into format required by LLM APIs.

    Args:
        image_url: Can be:
            - A file path (str)
            - A URL (str)
            - Base64 encoded image (str)
            - Raw bytes

    Returns:
        Dict with image type and properly structured image_url object.
    """
    if isinstance(image_url, bytes):
        base64_image = base64.b64encode(image_url).decode("utf-8")
        return create_data_uri("image/jpeg", base64_image)

    elif isinstance(image_url, str):
        if is_valid_image_path(image_url):
            mime_type = get_mime_type(image_url)
            with open(image_url, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")
                return create_data_uri(mime_type, base64_image)

        elif is_base64(image_url):
            return create_data_uri("image/jpeg", image_url)

        elif image_url.startswith(("http://", "https://")):
            return {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            }
        elif image_url.startswith("data:image"):
            return {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            }

        raise ValueError("Invalid image path or URL")

    raise ValueError(
        "Image input must be either bytes, file path, base64 string, or URL"
    )
