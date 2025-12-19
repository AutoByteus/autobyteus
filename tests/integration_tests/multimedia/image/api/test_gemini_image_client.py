import os
import pytest

from autobyteus.multimedia import image_client_factory, ImageGenerationResponse


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
async def test_gemini_generate_image(gemini_image_client):
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


@pytest.mark.asyncio
async def test_gemini_generate_image_with_inputs(gemini_image_client):
    """Ensures the client accepts input_images list without raising."""
    prompt = "Add stars to the night sky"
    response = await gemini_image_client.generate_image(
        prompt, input_image_urls=["https://example.com/placeholder.jpg"]
    )

    assert isinstance(response, ImageGenerationResponse)
    assert len(response.image_urls) > 0
