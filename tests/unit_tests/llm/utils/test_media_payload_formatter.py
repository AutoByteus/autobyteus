import pytest
import base64
import httpx
from pathlib import Path
from autobyteus.llm.utils.media_payload_formatter import (
    is_valid_media_path,
    is_base64,
    file_to_base64,
    url_to_base64,
    media_source_to_base64,
    media_source_to_data_uri,
)

# A valid 1x1 pixel red dot GIF, base64 encoded
VALID_BASE64_IMAGE = "R0lGODlhAQABAIAAAO/v7////yH5BAAHAP8ALAAAAAABAAEAAAICRAEAOw=="
# Sample image content for mock responses and file creation
IMAGE_BYTES = base64.b64decode(VALID_BASE64_IMAGE)
# Using the user-provided URL for testing the logic
USER_PROVIDED_IMAGE_URL = "https://127.0.0.1:51739/media/images/b132adbb-80e4-4faf-bd36-44d965d2e095.jpg"

@pytest.fixture
def temp_image_file(tmp_path: Path) -> Path:
    """Create a temporary image file for testing."""
    img_file = tmp_path / "test.png"
    img_file.write_bytes(IMAGE_BYTES)
    return img_file

@pytest.fixture
def temp_audio_file(tmp_path: Path) -> Path:
    """Create a temporary audio file for testing."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"dummy audio content")
    return audio_file

@pytest.fixture
def temp_video_file(tmp_path: Path) -> Path:
    """Create a temporary video file for testing."""
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"dummy video content")
    return video_file

def test_is_valid_media_path(temp_image_file: Path, temp_audio_file: Path, temp_video_file: Path, tmp_path: Path):
    assert is_valid_media_path(str(temp_image_file)) is True
    assert is_valid_media_path(str(temp_audio_file)) is True
    assert is_valid_media_path(str(temp_video_file)) is True
    assert is_valid_media_path("non_existent_file.jpg") is False
    assert is_valid_media_path(str(tmp_path)) is False  # Is a directory
    
    non_media_file = tmp_path / "test.txt"
    non_media_file.write_text("hello")
    assert is_valid_media_path(str(non_media_file)) is False

def test_is_base64():
    assert is_base64(VALID_BASE64_IMAGE) is True
    assert is_base64("this is not base64") is False
    assert is_base64(VALID_BASE64_IMAGE[:-1] + "!") is False # Invalid characters
    assert is_base64(VALID_BASE64_IMAGE[:-1]) is False # Invalid padding

def test_file_to_base64(temp_image_file: Path):
    result = file_to_base64(str(temp_image_file))
    assert result == VALID_BASE64_IMAGE
    
    with pytest.raises(FileNotFoundError):
        file_to_base64("non_existent_file.png")

@pytest.mark.asyncio
async def test_url_to_base64():
    # Mock transport to simulate network responses without actual network calls
    async def mock_transport(request: httpx.Request) -> httpx.Response:
        # Check for the user's localhost URL
        if "127.0.0.1" in str(request.url):
            return httpx.Response(200, content=IMAGE_BYTES)
        return httpx.Response(404)

    # Temporarily replace the module's client with a mocked one
    from autobyteus.llm.utils import media_payload_formatter
    original_client = media_payload_formatter._http_client
    # FIX: Wrap the handler in httpx.MockTransport
    media_payload_formatter._http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))

    # Test successful download from the user-provided URL
    result = await url_to_base64(USER_PROVIDED_IMAGE_URL)
    assert result == VALID_BASE64_IMAGE

    # Test failed download from a different URL
    with pytest.raises(httpx.HTTPStatusError):
        await url_to_base64("https://example.com/notfound.jpg")
    
    # Restore original client
    media_payload_formatter._http_client = original_client

@pytest.mark.asyncio
async def test_media_source_to_base64_orchestrator(temp_image_file: Path, temp_audio_file: Path):
    # Mock transport for URL testing
    async def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=IMAGE_BYTES)
    from autobyteus.llm.utils import media_payload_formatter
    original_client = media_payload_formatter._http_client
    # FIX: Wrap the handler in httpx.MockTransport
    media_payload_formatter._http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))

    # Test image file path
    result_from_file = await media_source_to_base64(str(temp_image_file))
    assert result_from_file == VALID_BASE64_IMAGE

    # Test audio file path
    audio_b64 = base64.b64encode(b"dummy audio content").decode("utf-8")
    result_from_audio = await media_source_to_base64(str(temp_audio_file))
    assert result_from_audio == audio_b64

    # Test user-provided URL
    result_from_url = await media_source_to_base64(USER_PROVIDED_IMAGE_URL)
    assert result_from_url == VALID_BASE64_IMAGE

    # Test existing base64
    result_from_base64 = await media_source_to_base64(VALID_BASE64_IMAGE)
    assert result_from_base64 == VALID_BASE64_IMAGE

    # Test invalid source
    with pytest.raises(ValueError):
        await media_source_to_base64("this is not a valid source")
        
    # Restore original client
    media_payload_formatter._http_client = original_client


@pytest.mark.asyncio
async def test_media_source_to_data_uri_orchestrator(temp_image_file: Path):
    async def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=IMAGE_BYTES,
            headers={"content-type": "image/jpeg"},
        )

    from autobyteus.llm.utils import media_payload_formatter

    original_client = media_payload_formatter._http_client
    media_payload_formatter._http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_transport)
    )

    result_from_data_uri = await media_source_to_data_uri("data:image/png;base64,abc123")
    assert result_from_data_uri == "data:image/png;base64,abc123"

    result_from_file = await media_source_to_data_uri(str(temp_image_file))
    assert result_from_file.startswith("data:image/png;base64,")

    result_from_url = await media_source_to_data_uri(USER_PROVIDED_IMAGE_URL)
    assert result_from_url.startswith("data:image/jpeg;base64,")

    result_from_base64 = await media_source_to_data_uri(VALID_BASE64_IMAGE)
    assert result_from_base64 == f"data:application/octet-stream;base64,{VALID_BASE64_IMAGE}"

    with pytest.raises(ValueError):
        await media_source_to_data_uri("not-a-valid-source")

    media_payload_formatter._http_client = original_client
