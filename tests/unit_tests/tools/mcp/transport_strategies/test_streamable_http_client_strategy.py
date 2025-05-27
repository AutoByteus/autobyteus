# file: autobyteus/tests/unit_tests/tools/mcp/transport_strategies/test_streamable_http_client_strategy.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from autobyteus.tools.mcp.types import StreamableHttpMcpServerConfig
from autobyteus.tools.mcp.transport_strategies import StreamableHttpClientStrategy

@pytest.fixture
def mock_http_config():
    return StreamableHttpMcpServerConfig(
        server_id="test_http_server",
        url="http://test.example.com/stream",
        headers={"X-API-KEY": "test_key"}
    )

@pytest.mark.asyncio
async def test_http_establish_connection_success(mock_http_config: StreamableHttpMcpServerConfig):
    strategy = StreamableHttpClientStrategy()
    
    mock_client_handle = AsyncMock()
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()
    mock_response_obj = MagicMock() # Third item from __aenter__ for HTTP
    
    mock_client_handle.__aenter__.return_value = (mock_read_stream, mock_write_stream, mock_response_obj)

    with patch('autobyteus.tools.mcp.transport_strategies.streamable_http_client_strategy.mcp_streamablehttp_client_factory', return_value=mock_client_handle) as mock_factory:
        client_handle, read_stream, write_stream = await strategy.establish_connection(mock_http_config)

        mock_factory.assert_called_once_with(
            mock_http_config.url,
            headers=mock_http_config.headers
        )
        mock_client_handle.__aenter__.assert_awaited_once()
        
        assert client_handle == mock_client_handle
        assert read_stream == mock_read_stream
        assert write_stream == mock_write_stream
        mock_client_handle.__aexit__.assert_not_called()

@pytest.mark.asyncio
async def test_http_establish_connection_aenter_fails(mock_http_config: StreamableHttpMcpServerConfig):
    strategy = StreamableHttpClientStrategy()
    mock_client_handle = AsyncMock()
    mock_client_handle.__aenter__.side_effect = RuntimeError("aenter failed")

    with patch('autobyteus.tools.mcp.transport_strategies.streamable_http_client_strategy.mcp_streamablehttp_client_factory', return_value=mock_client_handle):
        with pytest.raises(RuntimeError, match="Failed to enter StreamableHttp client context for server 'test_http_server': aenter failed"):
            await strategy.establish_connection(mock_http_config)
        
        mock_client_handle.__aexit__.assert_awaited_once()

