import os
import pytest
from unittest.mock import Mock, AsyncMock, patch # Added Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.webpage_image_downloader import WebPageImageDownloader

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def image_downloader_tool(): # Renamed fixture
    return WebPageImageDownloader()

@pytest.mark.asyncio
async def test_webpage_image_downloader(image_downloader_tool, mock_agent_context, tmp_path): # Added mock_agent_context, tmp_path
    url = "https://www.kaufland.de/" 
    save_dir = tmp_path / "kaufland_images" # Use tmp_path for save_dir

    # Mock Playwright interactions
    mock_page = AsyncMock()
    # Mock evaluate to return some image URLs
    mock_page.evaluate.return_value = [
        "https://example.com/image1.jpg", 
        "https://example.com/image2.png",
        "https://example.com/image3.svg" # SVG to be ignored
    ]
    # Mock screenshot to return dummy image bytes
    mock_page.screenshot.return_value = b"dummy_image_bytes"

    with patch.object(WebPageImageDownloader, 'initialize', AsyncMock()) as mock_initialize, \
         patch.object(WebPageImageDownloader, 'close', AsyncMock()), \
         patch.object(WebPageImageDownloader, 'page', new_callable=lambda: mock_page):

        saved_paths = await image_downloader_tool.execute(
            mock_agent_context, # Added mock_agent_context
            url=url, 
            save_dir=str(save_dir)
        )

    assert len(saved_paths) == 2, "Should download 2 non-SVG images"
    
    mock_initialize.assert_called_once()
    # page.goto is called for initial page and then for each image
    assert mock_page.goto.call_count == 1 (initial) + 2 (images)

    for i, path in enumerate(saved_paths):
        assert os.path.exists(path), f"Downloaded image not found at {path}"
        assert str(save_dir) in path, f"Image not saved in specified directory: {path}"
        file_ext = os.path.splitext(path)[1]
        assert file_ext in ['.jpg', '.png'], f"Unexpected image format: {path}"
        # Verify dummy content was written
        with open(path, "rb") as f:
            assert f.read() == b"dummy_image_bytes"

def test_tool_usage_xml(image_downloader_tool):
    usage_xml = image_downloader_tool.tool_usage_xml()
    assert "WebPageImageDownloader: Downloads images (excluding SVGs)" in usage_xml
    assert '<command name="WebPageImageDownloader">' in usage_xml
    assert '<arg name="url">webpage_url</arg>' in usage_xml
    assert '<arg name="save_dir">path/to/save/directory</arg>' in usage_xml
