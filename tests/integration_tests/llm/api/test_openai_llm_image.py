import pytest
from pathlib import Path
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel


@pytest.fixture
def set_openai_env(monkeypatch):
    # Set a dummy API key for testing
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "",
    )


@pytest.fixture
def test_image_path():
    # Create a test directory if it doesn't exist
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)

    # Create a small test image
    image_path = test_dir / "test_image.jpg"
    if not image_path.exists():
        # Create a 1x1 pixel black JPEG
        from PIL import Image

        img = Image.new("RGB", (1, 1), color="black")
        img.save(image_path)

    return str(image_path)


@pytest.fixture
def openai_llm(set_openai_env):
    system_message = "You are a helpful assistant."
    return OpenAILLM(
        model_name=LLMModel.CHATGPT_4O_LATEST_API, system_message=system_message
    )


@pytest.fixture
def multiple_test_images(test_image_path):
    test_dir = Path(test_image_path).parent
    paths = []

    # Create multiple test images
    for i in range(2):
        image_path = test_dir / f"test_image_{i}.jpg"
        if not image_path.exists():
            from PIL import Image

            img = Image.new("RGB", (1, 1), color="black")
            img.save(image_path)
        paths.append(str(image_path))

    return paths


@pytest.mark.asyncio
async def test_openai_llm_with_image(openai_llm, test_image_path):
    user_message = "What's in this image?"
    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=[test_image_path]
    )

    assert isinstance(response, str)
    assert len(response) > 0
    assert len(openai_llm.messages) == 3  # System + User + Assistant
    assert isinstance(
        openai_llm.messages[-2].content, list
    )  # Content should be list with text and image


@pytest.mark.asyncio
async def test_openai_llm_with_image_url(openai_llm):
    user_message = "What's in this image?"
    url_path = "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_1280.jpg"
    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=[url_path]
    )

    assert isinstance(response, str)
    assert len(response) > 0
    assert len(openai_llm.messages) == 3  # System + User + Assistant
    assert isinstance(
        openai_llm.messages[-2].content, list
    )  # Content should be list with text and image


@pytest.mark.asyncio
async def test_openai_llm_with_multiple_images(openai_llm, multiple_test_images):
    user_message = "Describe these images"
    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=multiple_test_images
    )

    assert isinstance(response, str)
    assert len(response) > 0
    assert (
        len(openai_llm.messages[-2].content) == len(multiple_test_images) + 1
    )  # Text + Images


@pytest.mark.asyncio
async def test_openai_llm_streaming_with_image(openai_llm, test_image_path):
    user_message = "What do you see in this image?"
    complete_response = ""

    async for token in openai_llm._stream_user_message_to_llm(
        user_message=user_message, file_paths=[test_image_path]
    ):
        assert isinstance(token, str)
        complete_response += token

    assert len(complete_response) > 0
    # assert isinstance(openai_llm.messages[-2].content, list)
    # assert len(openai_llm.messages[-2].content) == 2  # Text + Image


@pytest.mark.asyncio
async def test_openai_llm_with_invalid_image_path(openai_llm):
    user_message = "What's in this image?"
    invalid_path = "nonexistent_image.jpg"

    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, file_paths=[invalid_path]
    )

    assert isinstance(response, str)
    assert len(openai_llm.messages[-2].content) == 1  # Only text, no image


@pytest.mark.asyncio
async def test_cleanup(openai_llm, test_image_path):
    # Test cleanup after using images
    await openai_llm._send_user_message_to_llm(
        user_message="Test cleanup", file_paths=[test_image_path]
    )
    await openai_llm.cleanup()

    # Verify cleanup was successful
    assert len(openai_llm.messages) > 0  # Messages should still exist after cleanup
