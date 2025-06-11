# file: autobyteus/tests/unit_tests/tools/mcp/test_connection_manager.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call
from contextlib import AsyncExitStack

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
    strategy.create_client_handle = AsyncMock()
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
    MockHttpStrategy.return_value = AsyncMock(spec=McpTransportClientStrategy)
    MockSseStrategy.return_value = AsyncMock(spec=McpTransportClientStrategy)

    if McpConnectionManager in McpConnectionManager._instances:
        del McpConnectionManager._instances[McpConnectionManager]
    
    return McpConnectionManager(config_service=mock_config_service)

@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.connection_manager.ClientSession', new=MockClientSession)
@patch('autobyteus.tools.mcp.connection_manager.AsyncExitStack')
async def test_get_session_new_session_success(MockAsyncExitStack, connection_manager: McpConnectionManager, mock_config_service):
    server_id = "stdio_server"
    mock_config = StdioMcpServerConfig(server_id=server_id, command="test_cmd", transport_type=McpTransportType.STDIO)
    mock_config_service.get_config.return_value = mock_config

    mock_exit_stack_instance = AsyncMock(spec=AsyncExitStack)
    MockAsyncExitStack.return_value = mock_exit_stack_instance
    
    mock_transport_handle = AsyncMock()
    stdio_strategy = connection_manager._transport_strategies[McpTransportType.STDIO]
    stdio_strategy.create_client_handle.return_value = mock_transport_handle

    mock_read_stream, mock_write_stream = MagicMock(), MagicMock()
    mock_exit_stack_instance.enter_async_context.side_effect = [
        (mock_read_stream, mock_write_stream), # Result of entering transport_handle
        AsyncMock(spec=MockClientSession)     # Result of entering ClientSession
    ]
    
    mock_session_instance = AsyncMock()
    MockClientSession.return_value = mock_session_instance

    session = await connection_manager.get_session(server_id)

    # Assertions
    mock_config_service.get_config.assert_called_once_with(server_id)
    stdio_strategy.create_client_handle.assert_awaited_once_with(mock_config)
    
    MockAsyncExitStack.assert_called_once() # Ensure a new stack was created
    
    # Check that the stack was used to enter contexts
    mock_exit_stack_instance.enter_async_context.assert_has_awaits([
        call(mock_transport_handle),
        call(mock_session_instance)
    ])

    MockClientSession.assert_called_once_with(mock_read_stream, mock_write_stream)

    assert session == mock_session_instance
    assert server_id in connection_manager._managed_connections
    stored_session, stored_stack = connection_manager._managed_connections[server_id]
    assert stored_session == mock_session_instance
    assert stored_stack == mock_exit_stack_instance


@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.connection_manager.ClientSession', new=MockClientSession)
async def test_get_session_existing_session(connection_manager: McpConnectionManager, mock_config_service):
    server_id = "existing_server"
    mock_existing_session = AsyncMock()
    mock_existing_stack = AsyncMock()
    connection_manager._managed_connections[server_id] = (mock_existing_session, mock_existing_stack)

    session = await connection_manager.get_session(server_id)

    assert session == mock_existing_session
    mock_config_service.get_config.assert_not_called()
    for strategy in connection_manager._transport_strategies.values():
        strategy.create_client_handle.assert_not_called()


@pytest.mark.asyncio
async def test_get_session_config_not_found(connection_manager: McpConnectionManager, mock_config_service):
    server_id = "not_found_server"
    mock_config_service.get_config.return_value = None
    with pytest.raises(ValueError, match=f"MCP configuration not found for server_id: {server_id}"):
        await connection_manager.get_session(server_id)


@pytest.mark.asyncio
@patch('autobyteus.tools.mcp.connection_manager.AsyncExitStack')
async def test_get_session_creation_fails(MockAsyncExitStack, connection_manager: McpConnectionManager, mock_config_service):
    server_id = "fail_server"
    mock_config = StdioMcpServerConfig(server_id=server_id, command="cmd")
    mock_config_service.get_config.return_value = mock_config
    
    mock_exit_stack_instance = AsyncMock(spec=AsyncExitStack)
    MockAsyncExitStack.return_value = mock_exit_stack_instance

    stdio_strategy = connection_manager._transport_strategies[McpTransportType.STDIO]
    # Simulate strategy failing to create the handle
    stdio_strategy.create_client_handle.side_effect = RuntimeError("Handle creation failed")

    with pytest.raises(RuntimeError, match="Handle creation failed"):
        await connection_manager.get_session(server_id)

    # Assert that the exit stack was closed even on failure
    mock_exit_stack_instance.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_session(connection_manager: McpConnectionManager):
    server_id = "server_to_close"
    mock_session_instance = AsyncMock()
    mock_exit_stack_instance = AsyncMock(spec=AsyncExitStack)
    connection_manager._managed_connections[server_id] = (mock_session_instance, mock_exit_stack_instance)

    await connection_manager.close_session(server_id)

    mock_exit_stack_instance.aclose.assert_awaited_once()
    assert server_id not in connection_manager._managed_connections


@pytest.mark.asyncio
async def test_close_all_sessions(connection_manager: McpConnectionManager):
    mock_stack1, mock_stack2 = AsyncMock(spec=AsyncExitStack), AsyncMock(spec=AsyncExitStack)
    connection_manager._managed_connections = {
        "s1": (AsyncMock(), mock_stack1),
        "s2": (AsyncMock(), mock_stack2)
    }

    await connection_manager.close_all_sessions()

    mock_stack1.aclose.assert_awaited_once()
    mock_stack2.aclose.assert_awaited_once()
    assert not connection_manager._managed_connections
