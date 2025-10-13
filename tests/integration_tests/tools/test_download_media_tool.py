import pytest
import os
import requests
from pathlib import Path
from unittest.mock import MagicMock

from autobyteus.tools.multimedia.download_media_tool import DownloadMediaTool

# --- Test Configuration ---
LOCAL_SERVER_BASE_URL = "http://192.168.2.124:29695"
LOCAL_FILES_TO_TEST = [
    (f"{LOCAL_SERVER_BASE_URL}/rest/files/images/fdb2023c-0295-49ab-98c4-16f0c94eaaa3.png", "test-image", ".png"),
    (f"{LOCAL_SERVER_BASE_URL}/rest/files/audio/8a4dbe88-78ec-4b3f-a27b-e3805492bde6.wav", "test-audio", ".wav"),
]
PUBLIC_PDF_URL = "https://arxiv.org/pdf/1706.03762"

# --- Pytest Fixtures ---
@pytest.fixture
def download_tool() -> DownloadMediaTool:
    """Provides an instance of the DownloadMediaTool for testing."""
    return DownloadMediaTool()

@pytest.fixture
def mock_context() -> MagicMock:
    """Provides a mock AgentContext, as the tool doesn't need a real one."""
    context = MagicMock()
    context.agent_id = "test-agent-123"
    return context

# --- Integration Tests ---

@pytest.mark.asyncio
@pytest.mark.parametrize("url, filename, expected_ext", LOCAL_FILES_TO_TEST)
async def test_download_media_tool_local_files(
    download_tool: DownloadMediaTool,
    mock_context: MagicMock,
    tmp_path: Path,
    url: str,
    filename: str,
    expected_ext: str,
):
    """
    Tests downloading various media types (image, audio) from the local test server.
    This test will now attempt to download directly without checking server availability first.
    """
    # Act: Execute the tool to download the file into a temporary directory
    try:
        result_message = await download_tool.execute(
            context=mock_context,
            url=url,
            filename=filename,
            folder=str(tmp_path)
        )
    except Exception as e:
        pytest.fail(f"Downloading from local URL '{url}' failed unexpectedly. Ensure the server is running and accessible. Error: {e}")
        
    # Assert: Verify the result and the downloaded file
    assert result_message.startswith("Successfully downloaded file to:")
    
    # Extract path from result message and create a Path object for easier handling
    file_path_str = result_message.replace("Successfully downloaded file to: ", "").strip()
    file_path = Path(file_path_str)
    
    assert file_path.exists(), f"Downloaded file should exist at {file_path}"
    assert file_path.is_file(), "Downloaded path should point to a file"
    assert file_path.stat().st_size > 0, "Downloaded file should not be empty"
    assert file_path.name.startswith(filename), f"Filename should start with '{filename}'"
    assert file_path.suffix == expected_ext, f"File extension should be '{expected_ext}'"
    assert str(tmp_path) in str(file_path), "File should be saved in the specified temporary folder"

@pytest.mark.asyncio
async def test_download_media_tool_public_pdf(
    download_tool: DownloadMediaTool,
    mock_context: MagicMock,
    tmp_path: Path
):
    """
    Tests downloading a PDF from a public URL (arxiv.org).
    This test relies on public internet access to run.
    """
    # Arrange
    url = PUBLIC_PDF_URL
    filename = "attention-is-all-you-need"
    expected_ext = ".pdf"
    
    # Act
    try:
        result_message = await download_tool.execute(
            context=mock_context,
            url=url,
            filename=filename,
            folder=str(tmp_path)
        )
    except Exception as e:
        pytest.fail(f"Downloading from public URL failed. This may be due to a network issue or a change in the source URL. Error: {e}")
        
    # Assert
    assert result_message.startswith("Successfully downloaded file to:")
    
    file_path_str = result_message.replace("Successfully downloaded file to: ", "").strip()
    file_path = Path(file_path_str)
    
    assert file_path.exists(), f"Downloaded PDF should exist at {file_path}"
    assert file_path.is_file(), "Downloaded path should point to a file"
    assert file_path.stat().st_size > 100000, "Downloaded PDF file should have a reasonable size (e.g., >100KB)"
    assert file_path.name.startswith(filename), f"Filename should start with '{filename}'"
    assert file_path.suffix == expected_ext, "File extension should be '.pdf'"
    assert str(tmp_path) in str(file_path), "File should be saved in the specified temporary folder"
