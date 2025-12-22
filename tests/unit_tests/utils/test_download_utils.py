import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import aiohttp
from autobyteus.utils.download_utils import download_file_from_url

# Helper to create a mock response context manager
class MockResponse:
    def __init__(self, status=200, content=b"data"):
        self.status = status
        self._content = content
        self.content = MagicMock()
        
        # Mock iter_chunked
        async def iter_chunked(n):
             yield self._content
        self.content.iter_chunked = iter_chunked

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.mark.asyncio
async def test_download_file_success(tmp_path):
    url = "http://example.com/test.png"
    file_path = tmp_path / "test.png"
    mock_content = b"fake image content"

    # We patch ClientSession.get. Since it returns a context manager, we return our helper.
    with patch("aiohttp.ClientSession.get", return_value=MockResponse(status=200, content=mock_content)):
         await download_file_from_url(url, file_path)

    assert file_path.exists()
    assert file_path.read_bytes() == mock_content

@pytest.mark.asyncio
async def test_download_file_http_error(tmp_path):
    url = "http://example.com/404.png"
    file_path = tmp_path / "404.png"

    with patch("aiohttp.ClientSession.get", return_value=MockResponse(status=404)):
        with pytest.raises(IOError, match="HTTP 404"):
            await download_file_from_url(url, file_path)
    
    assert not file_path.exists()

@pytest.mark.asyncio
async def test_download_file_cleanup_on_exception(tmp_path):
    url = "http://example.com/error.png"
    file_path = tmp_path / "error.png"

    # Simulate exception during streaming
    mock_resp = MockResponse(status=200)
    async def broken_iter(n):
        yield b"partial"
        raise ConnectionError("Broken pipe")
    mock_resp.content.iter_chunked = broken_iter

    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        with pytest.raises(ConnectionError):
            await download_file_from_url(url, file_path)
    
    # Verify file was cleaned up
    assert not file_path.exists()
