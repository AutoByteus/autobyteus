import base64
from typing import Dict, Union
from pathlib import Path


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


def process_image(image_input: Union[str, bytes]) -> Dict:
    """
    Process image input into format required by OpenAI API.

    Args:
        image_input: Can be:
            - A file path (str)
            - A URL (str)
            - Base64 encoded image (str)
            - Raw bytes

    Returns:
        Dict with image type and directly accessible data URL if applicable.
    """
    if isinstance(image_input, bytes):
        base64_image = base64.b64encode(image_input).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{base64_image}",
        }

    elif isinstance(image_input, str):
        if is_valid_image_path(image_input):
            with open(image_input, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")
                return {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                }

        elif is_base64(image_input):
            return {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{image_input}",
            }

        elif image_input.startswith(("http://", "https://", "data:image")):
            return {"type": "image_url", "image_url": image_input}

        raise ValueError("Invalid image path or URL")

    raise ValueError(
        "Image input must be either bytes, file path, base64 string, or URL"
    )
