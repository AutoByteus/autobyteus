# file: autobyteus/tests/unit_tests/tools/mcp/transport_strategies/test_stdio_client_strategy.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from autobyteus.tools.mcp.types import BaseMcpConfig, StdioMcpServerConfig
from autobyteus.tools.mcp.transport_strategies import StdioClientStrategy
from mcp import StdioServerParameters # This is a class from the mcp library

@pytest.fixture
def mock_stdio_config():
    return StdioMcpServerConfig(
        server_id="test_stdio_server",
        command="python",
        args=["-m", "dummy_server"],
        env={"TEST_VAR": "test_val"},
        cwd="/test/cwd"
    )

@pytest.mark.asyncio
async def test_stdio_create_client_handle_success(mock_stdio_config: StdioMcpServerConfig):
    strategy = StdioClientStrategy()
    
    # The factory returns the handle, which is a context manager
    mock_client_handle = AsyncMock()

    with patch('autobyteus.tools.mcp.transport_strategies.stdio_client_strategy.mcp_stdio_client_factory', return_value=mock_client_handle) as mock_factory, \
         patch('autobyteus.tools.mcp.transport_strategies.stdio_client_strategy.StdioServerParameters') as mock_stdio_params_class:
        
        mock_stdio_params_instance = MagicMock()
        mock_stdio_params_class.return_value = mock_stdio_params_instance

        # The method now only creates and returns the handle
        returned_handle = await strategy.create_client_handle(mock_stdio_config)

        # Assert that the parameters were prepared correctly
        mock_stdio_params_class.assert_called_once_with(
            command=mock_stdio_config.command,
            args=mock_stdio_config.args,
            env=mock_stdio_config.env,
            cwd=mock_stdio_config.cwd
        )
        # Assert that the factory was called with the parameters
        mock_factory.assert_called_once_with(mock_stdio_params_instance)
        
        # Assert that the returned handle is the one from the factory
        assert returned_handle == mock_client_handle
        
        # The strategy no longer enters or exits the context
        mock_client_handle.__aenter__.assert_not_called()
        mock_client_handle.__aexit__.assert_not_called()


@pytest.mark.asyncio
async def test_stdio_create_client_handle_wrong_config_type(mock_stdio_config: StdioMcpServerConfig):
    strategy = StdioClientStrategy()
    
    class NotStdioConfig:
        def __init__(self, server_id): self.server_id = server_id
        # This mock config lacks the 'command', 'args', etc. attributes

    config_lacking_attrs = NotStdioConfig(server_id="lacking_attrs")
    
    with pytest.raises(AttributeError):
         await strategy.create_client_handle(config_lacking_attrs) # type: ignore
