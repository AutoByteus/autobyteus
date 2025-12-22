import base64
import os
import re
from pathlib import Path
from urllib.request import urlopen

import pytest

from autobyteus.multimedia import image_client_factory, ImageGenerationResponse


_DATA_URI_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$")
_ONE_BY_ONE_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)


def _extension_from_mime(mime_type: str | None) -> str:
    if not mime_type:
        return "bin"
    if mime_type in {"image/jpeg", "image/jpg"}:
        return "jpg"
    if mime_type == "image/png":
        return "png"
    if mime_type == "image/webp":
        return "webp"
    if mime_type == "image/gif":
        return "gif"
    return "bin"


def _image_bytes_from_uri(image_uri: str) -> tuple[bytes, str | None]:
    match = _DATA_URI_RE.match(image_uri)
    if match:
        return base64.b64decode(match.group("data")), match.group("mime")
    with urlopen(image_uri, timeout=30) as response:
        return response.read(), response.headers.get("Content-Type")


def _save_image_to_temp(image_uri: str, tmp_path: Path, name: str) -> Path:
    image_bytes, mime_type = _image_bytes_from_uri(image_uri)
    assert image_bytes, "Gemini returned an empty image payload."
    extension = _extension_from_mime(mime_type)
    output_path = tmp_path / f"{name}.{extension}"
    output_path.write_bytes(image_bytes)
    return output_path


@pytest.fixture(scope="module")
def set_gemini_env():
    """Skip if neither Vertex nor API-key credentials are configured."""
    has_vertex = bool(os.getenv("VERTEX_AI_PROJECT") and os.getenv("VERTEX_AI_LOCATION"))
    has_api_key = bool(os.getenv("GEMINI_API_KEY"))

    if not (has_vertex or has_api_key):
        pytest.skip(
            "Gemini credentials not set. Provide VERTEX_AI_PROJECT & VERTEX_AI_LOCATION "
            "or GEMINI_API_KEY to run Gemini image integration tests."
        )


@pytest.fixture
def gemini_image_client(set_gemini_env):
    """Provides a Gemini image client from the factory."""
    return image_client_factory.create_image_client("gemini-3-pro-image-preview")


@pytest.mark.asyncio
async def test_gemini_generate_image(gemini_image_client, tmp_path):
    """Tests successful image generation with Gemini 3 Pro Image (Nano Banana Pro)."""
    prompt = "A watercolor painting of a lighthouse at dusk"
    response = await gemini_image_client.generate_image(prompt)

    assert isinstance(response, ImageGenerationResponse)
    assert isinstance(response.image_urls, list)
    assert len(response.image_urls) > 0

    first = response.image_urls[0]
    assert isinstance(first, str)
    # Gemini may return data: URIs (Vertex inline) or https URLs (AI Studio); accept either.
    assert first.startswith("data:") or "://" in first
    saved_path = _save_image_to_temp(first, tmp_path, "gemini_generate_image")
    assert saved_path.exists()
    assert saved_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_gemini_generate_image_with_inputs(gemini_image_client, tmp_path):
    """Ensures the client accepts input_images list without raising."""
    prompt = "Add stars to the night sky"
    input_path = tmp_path / "input.png"
    input_path.write_bytes(base64.b64decode(_ONE_BY_ONE_PNG))
    response = await gemini_image_client.generate_image(
        prompt, input_image_urls=[str(input_path)]
    )

    assert isinstance(response, ImageGenerationResponse)
    assert len(response.image_urls) > 0
    saved_path = _save_image_to_temp(response.image_urls[0], tmp_path, "gemini_generate_image_with_inputs")
    assert saved_path.exists()
    assert saved_path.stat().st_size > 0
