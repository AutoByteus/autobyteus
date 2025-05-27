# file: autobyteus/tests/unit_tests/tools/mcp/test_connection_manager.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call

from autobyteus.tools.mcp.connection_manager import McpConnectionManager
from autobyteus.tools.mcp.config_service import McpConfigService
from autobyteus.tools.mcp.types import StdioMcpServerConfig, McpTransportType, BaseMcpConfig
from autobyteus.tools.mcp.transport_strategies import McpTransportClientStrategy

# Mock mcp.ClientSession as it's an external dependency
MockClientSession = AsyncMock() 

@pytest.fixture
def mock_config_service():
    return MagicMock(spec=McpConfigService)

@pytest.fixture
def mock_stdio_strategy_instance():
    strategy = AsyncMock(spec=McpTransportClientStrategy)
    strategy.establish_connection = AsyncMock()
    return strategy

@pytest.fixture
def mock_http_strategy_instance():
    strategy = AsyncMock(spec=McpTransportClientStrategy)
    strategy.establish_connection = AsyncMock()
    return strategy


@pytest.fixture
@patch('autobyteus.tools.mcp.connection_manager.StdioClientStrategy')
@patch('autobyteus.tools.mcp.connection_manager.StreamableHttpClientStrategy')
@patch('autobyteus.tools.mcp.connection_manager.SseClientStrategy')
def connection_manager(
    MockSseStrategy, MockHttpStrategy, MockStdioStrategy, 
    mock_config_service
) -> McpConnectionManager:
    # Return instances from the mocks
    MockStdioStrategy.return_value = mock_stdio_strategy_instance()
    MockHttpStrategy.return_value = mock_http_strategy_instance()
    MockSseStrategy.return_value = AsyncMock(spec=McpTransportClientStrategy) # For completeness

    # Clear singleton instance for fresh start in each test if manager is a true singleton
    if McpConnectionManager in McpConnectionManager._instances:
        del McpConnectionManager._instances[McpConnectionManager]
    
    return McpConnectionManager(config_service=mock_config_service)


@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.connection_manager.ClientSession', new=MockClientSession) # Patch ClientSession globally for these tests
async def test_get_session_new_stdio_session(connection_manager: McpConnectionManager, mock_config_service):
    server_id = "stdio_server"
    mock_config = StdioMcpServerConfig(server_id=server_id, command="test_cmd", transport_type=McpTransportType.STDIO) # transport_type set by __post_init__
    mock_config_service.get_config.return_value = mock_config

    mock_client_handle = AsyncMock()
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()
    
    # Get the actual stdio strategy instance used by the manager
    stdio_strategy = connection_manager._transport_strategies[McpTransportType.STDIO]
    stdio_strategy.establish_connection.return_value = (mock_client_handle, mock_read_stream, mock_write_stream)
    
    mock_session_instance = AsyncMock()
    MockClientSession.return_value = mock_session_instance # MockClientSession will be called with streams

    session = await connection_manager.get_session(server_id)

    mock_config_service.get_config.assert_called_once_with(server_id)
    stdio_strategy.establish_connection.assert_awaited_once_with(mock_config)
    MockClientSession.assert_called_once_with(mock_read_stream, mock_write_stream)
    mock_session_instance.initialize.assert_awaited_once()
    
    assert session == mock_session_instance
    assert connection_manager._active_sessions[server_id] == mock_session_instance
    assert connection_manager._managed_client_handles[server_id] == mock_client_handle

@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.connection_manager.ClientSession', new=MockClientSession)
async def test_get_session_existing_session(connection_manager: McpConnectionManager, mock_config_service):
    server_id = "existing_server"
    mock_existing_session = AsyncMock()
    connection_manager._active_sessions[server_id] = mock_existing_session

    session = await connection_manager.get_session(server_id)

    assert session == mock_existing_session
    mock_config_service.get_config.assert_not_called() # Should not try to create new
    # Ensure strategies are not called
    for strategy in connection_manager._transport_strategies.values():
        if hasattr(strategy, 'establish_connection'): # SseClientStrategy might not have it if strictly placeholder
            strategy.establish_connection.assert_not_called()


@pytest.mark.asyncio
async def test_get_session_config_not_found(connection_manager: McpConnectionManager, mock_config_service):
    server_id = "not_found_server"
    mock_config_service.get_config.return_value = None
    with pytest.raises(ValueError, match=f"MCP configuration not found for server_id: {server_id}"):
        await connection_manager.get_session(server_id)

@pytest.mark.asyncio
async def test_get_session_config_disabled(connection_manager: McpConnectionManager, mock_config_service):
    server_id = "disabled_server"
    mock_config = StdioMcpServerConfig(server_id=server_id, command="cmd", enabled=False)
    mock_config_service.get_config.return_value = mock_config
    with pytest.raises(ValueError, match=f"MCP server_id: '{server_id}' is disabled."):
        await connection_manager.get_session(server_id)

@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.connection_manager.ClientSession', new=MockClientSession)
async def test_get_session_strategy_fails(connection_manager: McpConnectionManager, mock_config_service):
    server_id = "strategy_fail_server"
    mock_config = StdioMcpServerConfig(server_id=server_id, command="cmd")
    mock_config_service.get_config.return_value = mock_config

    stdio_strategy = connection_manager._transport_strategies[McpTransportType.STDIO]
    stdio_strategy.establish_connection.side_effect = RuntimeError("Strategy connection failed")

    # Mock client_handle that might be returned before failure or during partial success
    mock_partial_client_handle = AsyncMock()
    stdio_strategy.establish_connection.return_value = (mock_partial_client_handle, None, None) # Simulate partial success before error
    
    with pytest.raises(RuntimeError, match="Failed to create MCP session for server_id 'strategy_fail_server'"):
        await connection_manager.get_session(server_id)
    
    # Check if __aexit__ was called on the partially created handle by the manager's error handling
    # This depends on how the error is raised relative to client_handle assignment.
    # If establish_connection itself raises, its internal finally should try to __aexit__.
    # If establish_connection returns a handle but then an error occurs in ConnectionManager before storing it,
    # ConnectionManager's try/except should call __aexit__.
    # Given the current structure, strategy itself tries to clean up if its __aenter__ (inside establish_connection) fails.
    # If establish_connection returns successfully but e.g. ClientSession init fails, ConnectionManager needs to clean.
    
    # For this specific test, if establish_connection raises, its own cleanup is primary.
    # Let's refine the test to check if establish_connection itself cleans up.
    # The strategy now includes its own __aexit__ call if __aenter__ fails.
    # So, we don't necessarily expect the manager to call __aexit__ on a handle it never fully received.
    # This part of the test might need more specific mocking of how the failure occurs.

    # If strategy.establish_connection returns client_handle, but then ClientSession init fails:
    MockClientSession.side_effect = RuntimeError("ClientSession init failed")
    stdio_strategy.establish_connection.side_effect = None # Reset side effect
    stdio_strategy.establish_connection.return_value = (mock_partial_client_handle, MagicMock(), MagicMock())

    with pytest.raises(RuntimeError, match="ClientSession init failed"):
        await connection_manager.get_session(server_id)
    
    # Now, ConnectionManager should have tried to clean up mock_partial_client_handle
    mock_partial_client_handle.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_session(connection_manager: McpConnectionManager):
    server_id = "server_to_close"
    mock_session_instance = AsyncMock()
    mock_client_handle_instance = AsyncMock()

    connection_manager._active_sessions[server_id] = mock_session_instance
    connection_manager._managed_client_handles[server_id] = mock_client_handle_instance

    await connection_manager.close_session(server_id)

    mock_session_instance.close.assert_awaited_once()
    mock_client_handle_instance.__aexit__.assert_awaited_once_with(None, None, None)
    assert server_id not in connection_manager._active_sessions
    assert server_id not in connection_manager._managed_client_handles

@pytest.mark.asyncio
async def test_close_all_sessions(connection_manager: McpConnectionManager):
    server1_id, server2_id = "s1", "s2"
    s1_session, s2_session = AsyncMock(), AsyncMock()
    s1_handle, s2_handle = AsyncMock(), AsyncMock()

    connection_manager._active_sessions = {server1_id: s1_session, server2_id: s2_session}
    connection_manager._managed_client_handles = {server1_id: s1_handle, server2_id: s2_handle}

    await connection_manager.close_all_sessions()

    s1_session.close.assert_awaited_once()
    s1_handle.__aexit__.assert_awaited_once_with(None, None, None)
    s2_session.close.assert_awaited_once()
    s2_handle.__aexit__.assert_awaited_once_with(None, None, None)
    
    assert not connection_manager._active_sessions
    assert not connection_manager._managed_client_handles

@pytest.mark.asyncio
async def test_cleanup_calls_close_all_sessions(connection_manager: McpConnectionManager):
    with patch.object(connection_manager, 'close_all_sessions', new_callable=AsyncMock) as mock_close_all:
        await connection_manager.cleanup()
        mock_close_all.assert_awaited_once()

