# file: autobyteus/tests/unit_tests/tools/mcp/transport_strategies/test_sse_client_strategy.py
import pytest
import asyncio
from unittest.mock import MagicMock

from autobyteus.tools.mcp.types import SseMcpServerConfig
from autobyteus.tools.mcp.transport_strategies import SseClientStrategy

@pytest.fixture
def mock_sse_config():
    return SseMcpServerConfig(
        server_id="test_sse_server",
        url="http://test.example.com/events",
        token="test_token"
    )

@pytest.mark.asyncio
async def test_sse_establish_connection_raises_not_implemented(mock_sse_config: SseMcpServerConfig):
    strategy = SseClientStrategy()
    
    with pytest.raises(NotImplementedError, match="SSE transport client strategy not fully implemented for server 'test_sse_server'"):
        await strategy.establish_connection(mock_sse_config)

