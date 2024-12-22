import pytest
import os
from pathlib import Path
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.models import LLMModel

TEST_IMAGE_PATH = str(
    Path(__file__).parent.parent.parent.parent / "resources" / "image_1.jpg"
)


@pytest.fixture
def set_mistral_env(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "")


@pytest.fixture
def pixtral_llm(set_mistral_env):
    """Fixture for testing Pixtral (vision) capabilities"""
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key:
        pytest.skip("Mistral API key not set. Skipping Pixtral tests.")
    return MistralLLM(model_name=LLMModel.PIXTRAL_LARGE_API)


@pytest.mark.asyncio
async def test_pixtral_with_image_url(pixtral_llm):
    """Test Pixtral multimodal capabilities"""
    # Setup
    user_message = "What do you see in this image?"
    image_url = "https://picsum.photos/id/237/200/300"

    # Test
    response = await pixtral_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=[image_url]
    )

    # Verify message format
    first_message = pixtral_llm.messages[0]
    content = first_message.content
    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == image_url

    # Verify response
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_pixtral_with_multiple_image_urls(pixtral_llm):
    """Test Pixtral multimodal capabilities with multiple images"""
    # Setup
    user_message = "What do you see in these images?"
    image_urls = [
        "https://picsum.photos/id/237/200/300",
        "https://picsum.photos/id/238/200/300",
    ]

    # Test
    response = await pixtral_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=image_urls
    )

    # Verify message format
    first_message = pixtral_llm.messages[0]
    content = first_message.content
    assert isinstance(content, list)
    assert len(content) == 3
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == image_urls[0]
    assert content[2]["type"] == "image_url"
    assert content[2]["image_url"]["url"] == image_urls[1]

    # Verify response
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_pixtral_invalid_inputs(pixtral_llm):
    """Test error handling for various invalid inputs"""
    # Setup
    user_message = "What do you see?"
    test_cases = [
        ("nonexistent.jpg", "Error processing image"),
        ("", "Invalid file path"),
        (None, "Invalid file path"),
        ("http://invalid.url/image.jpg", "Error processing image"),
    ]

    # Test each invalid input
    for invalid_input, expected_error in test_cases:
        with pytest.raises(ValueError) as exc_info:
            await pixtral_llm._send_user_message_to_llm(
                user_message=user_message, file_paths=[invalid_input]
            )
        assert expected_error in str(exc_info.value)

    # Test invalid message
    with pytest.raises(ValueError) as exc_info:
        await pixtral_llm._send_user_message_to_llm(
            user_message="", file_paths=[TEST_IMAGE_PATH]
        )
    assert "Invalid message" in str(exc_info.value)

    # Cleanup
    await pixtral_llm.cleanup()


@pytest.mark.asyncio
async def test_pixtral_streaming_with_image_url(pixtral_llm):
    user_message = "Describe this image."
    image_url = "https://picsum.photos/id/237/200/300"

    stream = pixtral_llm._stream_user_message_to_llm(
        user_message=user_message, file_paths=[image_url]
    )

    accumulated_content = ""
    async for chunk in stream:
        accumulated_content += chunk

    first_message = pixtral_llm.messages[0]
    content = first_message.content

    assert isinstance(content, list)
    assert len(content) == 2

    ## Verify message format
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == image_url

    # Verify streamed content
    assert isinstance(accumulated_content, str)
    assert len(accumulated_content) > 0


@pytest.mark.asyncio
async def test_pixtral_with_local_image(pixtral_llm):
    """Test Pixtral with local image file"""
    # Setup
    user_message = "What do you see in this image?"

    # Test
    response = await pixtral_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=[TEST_IMAGE_PATH]
    )

    # Verify message format
    first_message = pixtral_llm.messages[0]
    content = first_message.content
    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "base64" in content[1]["image_url"]["url"]

    # Verify response
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_pixtral_with_mixed_images(pixtral_llm):
    """Test Pixtral with mix of local and remote images"""
    # Setup
    user_message = "Compare these images"
    image_inputs = [TEST_IMAGE_PATH, "https://picsum.photos/id/237/200/300"]

    # Test
    response = await pixtral_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=image_inputs
    )

    # Verify message format
    first_message = pixtral_llm.messages[0]
    content = first_message.content
    assert isinstance(content, list)
    assert len(content) == 3
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "base64" in content[1]["image_url"]["url"]
    assert content[2]["type"] == "image_url"
    assert content[2]["image_url"]["url"] == image_inputs[1]

    # Verify response
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_pixtral_streaming_with_local_image(pixtral_llm):
    """Test Pixtral streaming with local image"""
    user_message = "Describe this image."

    stream = pixtral_llm._stream_user_message_to_llm(
        user_message=user_message, file_paths=[TEST_IMAGE_PATH]
    )

    accumulated_content = ""
    async for chunk in stream:
        accumulated_content += chunk

    # Verify message format
    first_message = pixtral_llm.messages[0]
    content = first_message.content
    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "base64" in content[1]["image_url"]["url"]

    # Verify streamed content
    assert isinstance(accumulated_content, str)
    assert len(accumulated_content) > 0


@pytest.mark.asyncio
async def test_pixtral_streaming_with_mixed_images(pixtral_llm):
    """Test Pixtral streaming with mixed images"""
    user_message = "Compare these images"
    image_inputs = [TEST_IMAGE_PATH, "https://picsum.photos/id/237/200/300"]

    stream = pixtral_llm._stream_user_message_to_llm(
        user_message=user_message, file_paths=image_inputs
    )

    accumulated_content = ""
    async for chunk in stream:
        accumulated_content += chunk

    # Verify message format
    first_message = pixtral_llm.messages[0]
    content = first_message.content
    assert isinstance(content, list)
    assert len(content) == 3
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "base64" in content[1]["image_url"]["url"]
    assert content[2]["type"] == "image_url"
    assert content[2]["image_url"]["url"] == image_inputs[1]

    # Verify streamed content
    assert isinstance(accumulated_content, str)
    assert len(accumulated_content) > 0
