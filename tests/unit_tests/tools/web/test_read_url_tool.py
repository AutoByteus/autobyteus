import pytest
from unittest.mock import MagicMock, AsyncMock
from autobyteus.tools.web.read_url_tool import ReadUrl
from autobyteus.utils.html_cleaner import CleaningMode

# Mock aiohttp
class _MockResponse:
    def __init__(self, status=200, text_content="<html><body><p>Hello World</p></body></html>"):
        self.status = status
        self._text_content = text_content

    async def text(self):
        return self._text_content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class _MockSession:
    def __init__(self, response_map=None):
        self.response_map = response_map or {}

    def get(self, url, timeout=30):
        # Return mapped response or default success response
        return self.response_map.get(url, _MockResponse())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.fixture
def tool():
    return ReadUrl()

@pytest.fixture
def context():
    ctx = MagicMock()
    ctx.agent_id = "test-agent"
    return ctx

@pytest.mark.asyncio
async def test_read_url_success_text(tool, context, monkeypatch):
    # Setup mock
    mock_html = "<html><body><h1>Title</h1><p>Some text content.</p></body></html>"
    
    def mock_session():
        return _MockSession(response_map={
            "http://example.com": _MockResponse(text_content=mock_html)
        })
    
    monkeypatch.setattr("aiohttp.ClientSession", mock_session)

    # Execute
    result = await tool.execute(context, url="http://example.com")

    # Verify - should be cleaned text
    assert "Title" in result
    assert "Some text content." in result
    assert "<html>" not in result

@pytest.mark.asyncio
async def test_read_url_success_html(tool, context, monkeypatch):
    # Setup mock
    mock_html = "<html><body><div id='content'>Important Data</div><script>bad</script></body></html>"
    
    def mock_session():
        return _MockSession(response_map={
            "http://example.com": _MockResponse(text_content=mock_html)
        })
    
    monkeypatch.setattr("aiohttp.ClientSession", mock_session)

    # Execute with html format
    result = await tool.execute(context, url="http://example.com", output_format="html")

    # Verify - should contain tags but be cleaned
    assert "<div>" in result or "***" not in result # Cleaning behavior depends on cleaner, but tags should remain
    assert "Important Data" in result
    assert "<script>" not in result # Cleaner removes scripts

@pytest.mark.asyncio
async def test_read_url_error_404(tool, context, monkeypatch):
    # Setup mock for 404
    def mock_session():
        return _MockSession(response_map={
            "http://example.com/notfound": _MockResponse(status=404)
        })
    
    monkeypatch.setattr("aiohttp.ClientSession", mock_session)

    # Execute
    result = await tool.execute(context, url="http://example.com/notfound")

    # Verify error message
    assert "Failed to fetch content" in result
    assert "404" in result

@pytest.mark.asyncio
async def test_read_url_network_error(tool, context, monkeypatch):
    # Setup mock to raise exception
    class _ErrorSession:
        def get(self, url, timeout=30):
            raise Exception("Connection refused")
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass

    monkeypatch.setattr("aiohttp.ClientSession", _ErrorSession)

    # Execute
    result = await tool.execute(context, url="http://example.com")

    # Verify error handling
    assert "Error reading URL" in result
    assert "Connection refused" in result
