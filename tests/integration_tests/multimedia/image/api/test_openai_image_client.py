import pytest
import os
import logging

from autobyteus.multimedia import image_client_factory, ImageGenerationResponse

@pytest.fixture(scope="module")
def set_openai_env():
    """Skips tests if the OpenAI API key is not set."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set. Skipping OpenAI image tests.")

@pytest.fixture
def gpt_image_15_client(set_openai_env):
    """Provides a gpt-image-1.5 client from the factory."""
    return image_client_factory.create_image_client("gpt-image-1.5")

@pytest.mark.asyncio
async def test_openai_generate_image(gpt_image_15_client):
    """Tests successful image generation with a gpt-image-1.5 model."""
    prompt = "A cute capybara wearing a top hat"
    response = await gpt_image_15_client.generate_image(prompt)

    assert isinstance(response, ImageGenerationResponse)
    assert isinstance(response.image_urls, list)
    assert len(response.image_urls) > 0
    first = response.image_urls[0]
    assert first.startswith("data:") or first.startswith("https://")

@pytest.mark.asyncio
async def test_openai_generate_image_with_input_image_warning(gpt_image_15_client, caplog):
    """Tests that a warning is logged when input_image_urls are provided to the generate endpoint."""
    prompt = "A photo of a cat"
    with caplog.at_level(logging.WARNING):
        response = await gpt_image_15_client.generate_image(prompt, input_image_urls=["dummy_path.jpg"])

        assert isinstance(response, ImageGenerationResponse)
        assert len(response.image_urls) > 0
        assert "The OpenAI `images.generate` API used by this client does not support input images" in caplog.text
