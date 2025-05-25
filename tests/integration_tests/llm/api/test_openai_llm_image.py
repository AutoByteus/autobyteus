import pytest
from pathlib import Path
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse # Added imports
from autobyteus.llm.utils.llm_config import LLMConfig # Added import
from autobyteus.llm.user_message import LLMUserMessage # Added import for LLMUserMessage


@pytest.fixture
def set_openai_env(monkeypatch):
    # Set a dummy API key for testing
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")) # Use actual env var or placeholder

@pytest.fixture
def test_image_path(tmp_path): # Use tmp_path fixture for temporary file creation
    # Create a small test image in a temporary directory
    image_path = tmp_path / "test_image.jpg"
    # Create a 1x1 pixel black JPEG
    from PIL import Image

    img = Image.new("RGB", (1, 1), color="black")
    img.save(image_path)

    return str(image_path)


@pytest.fixture
def openai_llm(set_openai_env):
    return OpenAILLM(model=LLMModel.CHATGPT_4O_LATEST_API, llm_config=LLMConfig())

@pytest.fixture
def multiple_test_images(tmp_path): # Use tmp_path fixture for temporary file creation
    paths = []

    # Create multiple test images in a temporary directory
    for i in range(2):
        image_path = tmp_path / f"test_image_{i}.jpg"
        from PIL import Image

        img = Image.new("RGB", (1, 1), color="black")
        img.save(image_path)
        paths.append(str(image_path))

    return paths


@pytest.mark.asyncio
async def test_openai_llm_with_image(openai_llm, test_image_path):
    user_message = "What's in this image?"
    # Use LLMUserMessage for inputs to public methods, and direct string/list to private _send/_stream
    # _send_user_message_to_llm expects content (str) and image_urls (Optional[List[str]])
    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, image_urls=[test_image_path] # Changed file_paths to image_urls
    )

    assert isinstance(response, CompleteResponse) # Expect CompleteResponse
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    assert len(openai_llm.messages) == 3  # System + User + Assistant
    # Content for LLM input with images is a list of dicts.
    assert isinstance(openai_llm.messages[-2].content, list)
    # Check that text part and image part are present in the list
    assert any(item.get("type") == "text" and item.get("text") == user_message for item in openai_llm.messages[-2].content)
    assert any(item.get("type") == "image_url" for item in openai_llm.messages[-2].content)


@pytest.mark.asyncio
async def test_openai_llm_with_image_url(openai_llm):
    user_message = "What's in this image?"
    url_path = "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_1280.jpg"
    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, image_urls=[url_path] # Changed file_paths to image_urls
    )

    assert isinstance(response, CompleteResponse) # Expect CompleteResponse
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    assert len(openai_llm.messages) == 3  # System + User + Assistant
    assert isinstance(
        openai_llm.messages[-2].content, list
    )  # Content should be list with text and image
    assert any(item.get("type") == "text" and item.get("text") == user_message for item in openai_llm.messages[-2].content)
    assert any(item.get("type") == "image_url" for item in openai_llm.messages[-2].content)


@pytest.mark.asyncio
async def test_openai_llm_with_multiple_images(openai_llm, multiple_test_images):
    user_message = "Describe these images"
    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, image_urls=multiple_test_images # Changed file_paths to image_urls
    )

    assert isinstance(response, CompleteResponse) # Expect CompleteResponse
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    # Text part + number of images
    assert (len(openai_llm.messages[-2].content) == len(multiple_test_images) + 1)
    assert any(item.get("type") == "text" and item.get("text") == user_message for item in openai_llm.messages[-2].content)
    assert len([item for item in openai_llm.messages[-2].content if item.get("type") == "image_url"]) == len(multiple_test_images)


@pytest.mark.asyncio
async def test_openai_llm_streaming_with_image(openai_llm, test_image_path):
    user_message = "What do you see in this image?"
    complete_response = ""

    async for chunk in openai_llm._stream_user_message_to_llm(
        user_message=user_message, image_urls=[test_image_path] # Changed file_paths to image_urls
    ):
        assert isinstance(chunk, ChunkResponse) # Expect ChunkResponse
        complete_response += chunk.content # Access content attribute

    assert len(complete_response) > 0
    assert isinstance(openai_llm.messages[-2].content, list)
    # Text part + one image
    assert len(openai_llm.messages[-2].content) == 2
    assert any(item.get("type") == "text" and item.get("text") == user_message for item in openai_llm.messages[-2].content)
    assert any(item.get("type") == "image_url" for item in openai_llm.messages[-2].content)


@pytest.mark.asyncio
async def test_openai_llm_with_invalid_image_path(openai_llm):
    user_message = "What's in this image?"
    invalid_path = "nonexistent_image.jpg"

    response = await openai_llm._send_user_message_to_llm(
        user_message=user_message, image_urls=[invalid_path] # Changed file_paths to image_urls
    )

    assert isinstance(response, CompleteResponse) # Expect CompleteResponse
    assert isinstance(response.content, str)
    # The image processing logic logs a warning and skips invalid images.
    # So the message history should only contain the text content.
    assert len(openai_llm.messages[-2].content) == 1
    assert openai_llm.messages[-2].content[0]["type"] == "text"
    assert openai_llm.messages[-2].content[0]["text"] == user_message


@pytest.mark.asyncio
async def test_cleanup(openai_llm, test_image_path):
    # Test cleanup after using images
    await openai_llm._send_user_message_to_llm(
        user_message="Test cleanup", image_urls=[test_image_path] # Changed file_paths to image_urls
    )
    await openai_llm.cleanup()

    # Verify cleanup was successful (messages list should be empty after cleanup)
    assert len(openai_llm.messages) == 0
