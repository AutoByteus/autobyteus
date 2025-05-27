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
async def test_stdio_establish_connection_success(mock_stdio_config: StdioMcpServerConfig):
    strategy = StdioClientStrategy()
    
    mock_client_handle = AsyncMock()
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()
    
    # __aenter__ should return the streams
    mock_client_handle.__aenter__.return_value = (mock_read_stream, mock_write_stream)

    with patch('autobyteus.tools.mcp.transport_strategies.stdio_client_strategy.mcp_stdio_client_factory', return_value=mock_client_handle) as mock_factory, \
         patch('autobyteus.tools.mcp.transport_strategies.stdio_client_strategy.StdioServerParameters') as mock_stdio_params_class:
        
        # Make StdioServerParameters constructor return a simple object for inspection
        mock_stdio_params_instance = MagicMock()
        mock_stdio_params_class.return_value = mock_stdio_params_instance

        client_handle, read_stream, write_stream = await strategy.establish_connection(mock_stdio_config)

        mock_stdio_params_class.assert_called_once_with(
            command=mock_stdio_config.command,
            args=mock_stdio_config.args,
            env=mock_stdio_config.env,
            cwd=mock_stdio_config.cwd
        )
        mock_factory.assert_called_once_with(mock_stdio_params_instance)
        mock_client_handle.__aenter__.assert_awaited_once()
        
        assert client_handle == mock_client_handle
        assert read_stream == mock_read_stream
        assert write_stream == mock_write_stream
        mock_client_handle.__aexit__.assert_not_called() # __aexit__ is called by ConnectionManager

@pytest.mark.asyncio
async def test_stdio_establish_connection_aenter_fails(mock_stdio_config: StdioMcpServerConfig):
    strategy = StdioClientStrategy()
    mock_client_handle = AsyncMock()
    # Make __aenter__ raise an exception
    mock_client_handle.__aenter__.side_effect = RuntimeError("aenter failed")

    with patch('autobyteus.tools.mcp.transport_strategies.stdio_client_strategy.mcp_stdio_client_factory', return_value=mock_client_handle):
        with pytest.raises(RuntimeError, match="Failed to enter Stdio client context for server 'test_stdio_server': aenter failed"):
            await strategy.establish_connection(mock_stdio_config)
        
        # Verify __aexit__ was called on failure
        mock_client_handle.__aexit__.assert_awaited_once()

@pytest.mark.asyncio
async def test_stdio_establish_connection_wrong_config_type(mock_stdio_config: StdioMcpServerConfig):
    strategy = StdioClientStrategy()
    # Create a config of a different type (mock or actual SseMcpServerConfig)
    wrong_config = MagicMock(spec=BaseMcpConfig) # Using BaseMcpConfig to ensure it's not Stdio
    wrong_config.server_id = "wrong_type_server"

    # The type hint in establish_connection is StdioMcpServerConfig.
    # Python's type system doesn't enforce this at runtime without isinstance.
    # The test for type checking is more about design and static analysis benefits.
    # If strict runtime check is desired, strategy would need `isinstance`.
    # For now, this test just shows that it *would* fail if it tried to access Stdio-specific fields.
    
    # Let's assume the mock_stdio_config is passed but we are testing the internal check logic
    # by temporarily enabling the runtime check in the strategy for this test.
    # This is a bit contrived. The main check is that the correct attributes are accessed.
    # If the wrong config type *that lacks StdioMcpServerConfig attributes* is passed, it will fail.

    # To properly test a TypeError if isinstance was used:
    # with pytest.raises(TypeError): await strategy.establish_connection(wrong_config)
    # Since we don't have isinstance in the strategy by default, we test attribute access:

    mock_client_handle = AsyncMock()
    mock_client_handle.__aenter__.return_value = (MagicMock(), MagicMock())
    
    with patch('autobyteus.tools.mcp.transport_strategies.stdio_client_strategy.mcp_stdio_client_factory', return_value=mock_client_handle), \
         patch('autobyteus.tools.mcp.transport_strategies.stdio_client_strategy.StdioServerParameters') as mock_stdio_params_class:
        
        # Pass a non-StdioMcpServerConfig that lacks 'command'
        class NotStdioConfig:
            def __init__(self, server_id): self.server_id = server_id
            # Missing 'command', 'args', etc.

        config_lacking_attrs = NotStdioConfig(server_id="lacking_attrs")
        
        with pytest.raises(AttributeError): # Expect AttributeError if wrong config type is passed
             await strategy.establish_connection(config_lacking_attrs) # type: ignore


