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
async def test_http_create_client_handle_success(mock_http_config: StreamableHttpMcpServerConfig):
    strategy = StreamableHttpClientStrategy()
    
    # The factory returns the handle, which is a context manager
    mock_client_handle = AsyncMock()
    
    with patch('autobyteus.tools.mcp.transport_strategies.streamable_http_client_strategy.mcp_streamablehttp_client_factory', return_value=mock_client_handle) as mock_factory:
        
        returned_handle = await strategy.create_client_handle(mock_http_config)

        # Assert that the factory was called correctly
        mock_factory.assert_called_once_with(
            mock_http_config.url,
            headers=mock_http_config.headers
        )
        
        # Assert that the returned handle is the one from the factory
        assert returned_handle == mock_client_handle

        # The strategy no longer enters or exits the context
        mock_client_handle.__aenter__.assert_not_called()
        mock_client_handle.__aexit__.assert_not_called()
