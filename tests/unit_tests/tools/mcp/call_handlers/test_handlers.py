# file: autobyteus/tests/unit_tests/tools/mcp/call_handlers/test_handlers.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.tools.mcp.call_handlers import (
    McpCallHandler,
    StdioMcpCallHandler,
    StreamableHttpMcpCallHandler,
    SseMcpCallHandler
)
from autobyteus.tools.mcp.types import (
    StdioMcpServerConfig,
    StreamableHttpMcpServerConfig,
    SseMcpServerConfig
)

# Mock the mcp.client session object
MockMcpClientSession = AsyncMock()

@pytest.fixture
def mock_stdio_config():
    return StdioMcpServerConfig(
        server_id="test-stdio",
        command="node",
        args=["server.js"],
        env={"VAR": "VAL"},
        cwd="/tmp"
    )

@pytest.fixture
def mock_http_config():
    return StreamableHttpMcpServerConfig(
        server_id="test-http",
        url="http://localhost:8080/mcp",
        headers={"X-Test": "true"}
    )

def test_mcp_call_handler_is_abc():
    """Tests that the base handler is an abstract base class."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class McpCallHandler with abstract method handle_call"):
        McpCallHandler() # type: ignore

@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.call_handlers.stdio_handler.stdio_client')
async def test_stdio_handler_call_tool(mock_stdio_client, mock_stdio_config):
    """Tests the StdioMcpCallHandler for a generic tool call."""
    handler = StdioMcpCallHandler()
    mock_session = MockMcpClientSession()
    mock_stdio_client.return_value.__aenter__.return_value = (MagicMock(), MagicMock()) # returns read/write streams
    
    # Patch the ClientSession within the handler's scope
    with patch('autobyteus.tools.mcp.call_handlers.stdio_handler.ClientSession') as MockCS:
        MockCS.return_value.__aenter__.return_value = mock_session
        
        await handler.handle_call(mock_stdio_config, "some_tool", {"arg": "val"})

        # Verify ClientSession was used as a context manager
        MockCS.assert_called_once()
        mock_session.call_tool.assert_awaited_once_with("some_tool", {"arg": "val"})
        mock_session.list_tools.assert_not_called()

@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.call_handlers.stdio_handler.stdio_client')
async def test_stdio_handler_list_tools(mock_stdio_client, mock_stdio_config):
    """Tests the StdioMcpCallHandler for the special 'list_tools' call."""
    handler = StdioMcpCallHandler()
    mock_session = MockMcpClientSession()
    mock_stdio_client.return_value.__aenter__.return_value = (MagicMock(), MagicMock())

    with patch('autobyteus.tools.mcp.call_handlers.stdio_handler.ClientSession') as MockCS:
        MockCS.return_value.__aenter__.return_value = mock_session
        
        await handler.handle_call(mock_stdio_config, "list_tools", {})
        
        MockCS.assert_called_once()
        mock_session.list_tools.assert_awaited_once()
        mock_session.call_tool.assert_not_called()

@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.call_handlers.streamable_http_handler.streamablehttp_client')
async def test_http_handler_call_tool(mock_http_client, mock_http_config):
    """Tests the StreamableHttpMcpCallHandler for a generic tool call."""
    handler = StreamableHttpMcpCallHandler()
    mock_session = MockMcpClientSession()
    mock_http_client.return_value.__aenter__.return_value = (MagicMock(), MagicMock())

    with patch('autobyteus.tools.mcp.call_handlers.streamable_http_handler.ClientSession') as MockCS:
        MockCS.return_value.__aenter__.return_value = mock_session

        await handler.handle_call(mock_http_config, "another_tool", {"key": "value"})

        mock_http_client.assert_called_once_with(mock_http_config.url, headers=mock_http_config.headers)
        MockCS.assert_called_once()
        mock_session.call_tool.assert_awaited_once_with("another_tool", {"key": "value"})
        mock_session.list_tools.assert_not_called()

@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.call_handlers.streamable_http_handler.streamablehttp_client')
async def test_http_handler_list_tools(mock_http_client, mock_http_config):
    """Tests the StreamableHttpMcpCallHandler for the special 'list_tools' call."""
    handler = StreamableHttpMcpCallHandler()
    mock_session = MockMcpClientSession()
    mock_http_client.return_value.__aenter__.return_value = (MagicMock(), MagicMock())

    with patch('autobyteus.tools.mcp.call_handlers.streamable_http_handler.ClientSession') as MockCS:
        MockCS.return_value.__aenter__.return_value = mock_session

        await handler.handle_call(mock_http_config, "list_tools", {})
        
        mock_http_client.assert_called_once_with(mock_http_config.url, headers=mock_http_config.headers)
        MockCS.assert_called_once()
        mock_session.list_tools.assert_awaited_once()
        mock_session.call_tool.assert_not_called()

@pytest.mark.asyncio
async def test_sse_handler_raises_not_implemented():
    """Tests that the SseMcpCallHandler is a placeholder."""
    handler = SseMcpCallHandler()
    mock_config = SseMcpServerConfig(server_id="test-sse", url="http://localhost/sse")
    with pytest.raises(NotImplementedError):
        await handler.handle_call(mock_config, "any_tool", {})
