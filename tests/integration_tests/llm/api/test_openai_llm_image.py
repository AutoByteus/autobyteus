import pytest
import os
from pathlib import Path
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))

@pytest.fixture
def test_image_path(tmp_path):
    image_path = tmp_path / "test_image.jpg"
    from PIL import Image
    img = Image.new("RGB", (10, 10), color="blue")
    img.save(image_path)
    return str(image_path)

@pytest.fixture
def openai_llm(set_openai_env):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key or openai_api_key == "YOUR_OPENAI_API_KEY":
        pytest.skip("OpenAI API key not set. Skipping OpenAILLM image tests.")
    return OpenAILLM(model=LLMModel['gpt-5.1'])

@pytest.fixture
def multiple_test_images(tmp_path):
    paths = []
    from PIL import Image
    img1 = Image.new("RGB", (10, 10), color="red")
    path1 = tmp_path / "test_image_1.jpg"
    img1.save(path1)
    paths.append(str(path1))

    img2 = Image.new("RGB", (10, 10), color="green")
    path2 = tmp_path / "test_image_2.jpg"
    img2.save(path2)
    paths.append(str(path2))
    return paths

@pytest.mark.asyncio
async def test_openai_llm_with_image(openai_llm, test_image_path):
    """Test sending a single local image file."""
    user_message = LLMUserMessage(
        content="What color is in this image?", 
        image_urls=[test_image_path]
    )
    response = await openai_llm.send_user_message(user_message)

    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert "blue" in response.content.lower()
    
    assert len(openai_llm.messages) == 3
    user_msg_in_history = openai_llm.messages[1]
    assert user_msg_in_history.content == user_message.content
    assert user_msg_in_history.image_urls == [test_image_path]

@pytest.mark.asyncio
async def test_openai_llm_with_image_url(openai_llm):
    """Test sending a single image via public URL."""
    user_message = LLMUserMessage(
        content="What is in this image?",
        image_urls=["https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/1280px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"]
    )
    response = await openai_llm.send_user_message(user_message)

    assert isinstance(response, CompleteResponse)
    assert "boardwalk" in response.content.lower() or "nature" in response.content.lower()
    
    assert len(openai_llm.messages) == 3
    user_msg_in_history = openai_llm.messages[1]
    assert user_msg_in_history.content == user_message.content
    assert user_msg_in_history.image_urls == user_message.image_urls

@pytest.mark.asyncio
async def test_openai_llm_with_multiple_images(openai_llm, multiple_test_images):
    """Test sending multiple local image files."""
    user_message = LLMUserMessage(
        content="What colors are in these images?", 
        image_urls=multiple_test_images
    )
    response = await openai_llm.send_user_message(user_message)

    assert isinstance(response, CompleteResponse)
    assert "red" in response.content.lower() and "green" in response.content.lower()
    
    assert len(openai_llm.messages) == 3
    user_msg_in_history = openai_llm.messages[1]
    assert user_msg_in_history.content == user_message.content
    assert user_msg_in_history.image_urls == multiple_test_images

@pytest.mark.asyncio
async def test_openai_llm_streaming_with_image(openai_llm, test_image_path):
    """Test streaming with a single local image file."""
    user_message = LLMUserMessage(
        content="What color is this image?", 
        image_urls=[test_image_path]
    )
    complete_response = ""

    async for chunk in openai_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        complete_response += chunk.content

    assert "blue" in complete_response.lower()
    
    assert len(openai_llm.messages) == 3
    user_msg_in_history = openai_llm.messages[1]
    assert user_msg_in_history.content == user_message.content
    assert user_msg_in_history.image_urls == [test_image_path]

@pytest.mark.asyncio
async def test_openai_llm_with_invalid_image_path(openai_llm):
    """Test that an invalid image path is handled gracefully."""
    invalid_path = "nonexistent/image/path.jpg"
    user_message = LLMUserMessage(
        content="What is in this image?", 
        image_urls=[invalid_path]
    )
    
    # The formatter will log an error for the invalid path but the API call should proceed with text only.
    # We expect an error from the OpenAI API if it requires an image but doesn't get one,
    # or a response based on text if it can proceed.
    # The key is that our code shouldn't crash.
    response = await openai_llm.send_user_message(user_message)
    
    assert isinstance(response, CompleteResponse)
    # The model will likely respond that it cannot see an image.
    assert "can't see" in response.content.lower() or "no image" in response.content.lower()

    # The message in history should still contain the invalid path as it was added before formatting.
    assert len(openai_llm.messages) == 3
    user_msg_in_history = openai_llm.messages[1]
    assert user_msg_in_history.content == user_message.content
    assert user_msg_in_history.image_urls == [invalid_path]

@pytest.mark.asyncio
async def test_cleanup(openai_llm, test_image_path):
    user_message = LLMUserMessage(content="Test cleanup", image_urls=[test_image_path])
    await openai_llm.send_user_message(user_message)
    await openai_llm.cleanup()

    assert len(openai_llm.messages) == 0
