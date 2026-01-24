import pytest
import os
import base64
from pathlib import Path
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def set_anthropic_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY"))

@pytest.fixture
def test_image_path():
    image_path = Path("tests/assets/sample_image.png")
    if not image_path.exists():
        # Create a dummy image if it doesn't exist for testing logic 
        # (though strictly we prefer a real one, this ensures tests don't fail just on missing asset)
        # However, for integration tests hitting API, we usually want real bytes. 
        # Assuming the environment has it or we skip.
        pass
    return str(image_path)

@pytest.fixture
def claude_llm(set_anthropic_env):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "YOUR_ANTHROPIC_API_KEY":
        pytest.skip("ANTHROPIC_API_KEY not set. Skipping ClaudeLLM image tests.")
    return ClaudeLLM(model=LLMModel['claude-4.5-sonnet']) # Use a vision-capable model

@pytest.fixture
def multiple_test_images(tmp_path):
    paths = []
    from PIL import Image
    try:
        img1 = Image.new("RGB", (10, 10), color="red")
        path1 = tmp_path / "test_image_1.jpg"
        img1.save(path1)
        paths.append(str(path1))

        img2 = Image.new("RGB", (10, 10), color="green")
        path2 = tmp_path / "test_image_2.jpg"
        img2.save(path2)
        paths.append(str(path2))
    except ImportError:
         pytest.skip("Pillow (PIL) not installed, cannot generate test images.")
    return paths

@pytest.mark.asyncio
async def test_claude_llm_with_image(claude_llm, test_image_path):
    """Test sending a single local image file."""
    if not Path(test_image_path).exists():
        pytest.skip(f"Test image not found at {test_image_path}")
        
    user_message = LLMUserMessage(
        content="What is in this image? Reply with 'image' in the text.", 
        image_urls=[test_image_path]
    )
    response = await claude_llm.send_user_message(user_message)

    assert isinstance(response, CompleteResponse)
    assert isinstance(response.content, str)
    assert len(response.content) > 0
    # We don't assert verification of content accuracy significantly, just that it processed it.

@pytest.mark.asyncio
async def test_claude_llm_with_image_base64(claude_llm, test_image_path):
    """Test sending a single image via base64."""
    if not Path(test_image_path).exists():
        pytest.skip(f"Test image not found at {test_image_path}")

    with open(test_image_path, "rb") as image_file:
        image_b64 = base64.b64encode(image_file.read()).decode("utf-8")
    
    user_message = LLMUserMessage(
        content="Describe this image shortly.",
        image_urls=[image_b64]
    )
    response = await claude_llm.send_user_message(user_message)

    assert isinstance(response, CompleteResponse)
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_claude_llm_with_multiple_images(claude_llm, multiple_test_images):
    """Test sending multiple local image files."""
    user_message = LLMUserMessage(
        content="What colors are in these images?", 
        image_urls=multiple_test_images
    )
    response = await claude_llm.send_user_message(user_message)

    assert isinstance(response, CompleteResponse)
    assert "red" in response.content.lower() or "green" in response.content.lower()

@pytest.mark.asyncio
async def test_claude_llm_streaming_with_image(claude_llm, test_image_path):
    """Test streaming with a single local image file."""
    if not Path(test_image_path).exists():
        pytest.skip(f"Test image not found at {test_image_path}")

    user_message = LLMUserMessage(
        content="What is in this image?", 
        image_urls=[test_image_path]
    )
    complete_response = ""

    async for chunk in claude_llm.stream_user_message(user_message):
        assert isinstance(chunk, ChunkResponse)
        complete_response += chunk.content

    assert len(complete_response) > 0

@pytest.mark.asyncio
async def test_claude_llm_unsupported_mime_type(claude_llm, tmp_path):
    """Test that unsupported MIME types are handled (e.g. defaulted to jpeg or handled gracefully)."""
    # Create a dummy bitmap file (not supported by default, usually)
    # Actually, let's just create a text file with .bmp extension to trick detection? 
    # Or use a known unsupported extension like .tiff if not in allowed list.
    # Our allowed list: {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    
    # We will simulate a file that gets typed as 'image/bmp' if possible, or just force a mock?
    # Easier to mock internal method, but integration test should rely on real behavior.
    # Let's write a file with .bmp extension.
    
    bmp_path = tmp_path / "test.bmp"
    # Write some random bytes
    bmp_path.write_bytes(b"BM" + b"\x00" * 50)
    
    # The `is_valid_media_path` might reject it if we only allow specific extensions there.
    # Let's check `is_valid_media_path` in `media_payload_formatter.py`.
    # It allows: .jpg, .jpeg, .png, .gif, .webp. 
    # So .bmp will fail `is_valid_media_path` and `media_source_to_base64` will raise ValueError.
    
    # Wait, if `media_source_to_base64` raises, we catch it in `_format_anthropic_messages` and log error.
    # So the test should pass and just send text.
    
    user_message = LLMUserMessage(
        content="Ignore the image failure, just say hello.", 
        image_urls=[str(bmp_path)]
    )
    
    response = await claude_llm.send_user_message(user_message)
    assert isinstance(response, CompleteResponse)
    assert "hello" in response.content.lower()
