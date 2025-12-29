# file: autobyteus/tests/unit_tests/agent/runtime/test_agent_worker.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call

from autobyteus.agent.runtime.agent_worker import AgentWorker
from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import WorkerEventDispatcher
from autobyteus.agent.events.agent_events import (
    UserMessageReceivedEvent, AgentErrorEvent
)
from autobyteus.agent.handlers import EventHandlerRegistry
from autobyteus.agent.bootstrap_steps.agent_bootstrapper import AgentBootstrapper
from autobyteus.agent.status.status_enum import AgentStatus

# Module-scoped thread pool manager to avoid creating/destroying threads for every test.
@pytest.fixture(scope="module", autouse=True)
def module_scoped_thread_pool_manager():
    """Ensure AgentThreadPoolManager is managed at the module level for all tests."""
    if hasattr(AgentThreadPoolManager, '_instances'):
        AgentThreadPoolManager._instances.clear()
        
    manager = AgentThreadPoolManager(max_workers=3)
    yield manager
    if not manager._is_shutdown:
        manager.shutdown(wait=True)
    if hasattr(AgentThreadPoolManager, '_instances'):
        AgentThreadPoolManager._instances.clear()

@pytest.fixture
def mock_dispatcher():
    """Provides a mock WorkerEventDispatcher."""
    return AsyncMock(spec=WorkerEventDispatcher)

@pytest.fixture
def agent_worker(agent_context, mock_dispatcher):
    """
    Provides an AgentWorker instance with a mocked dispatcher.
    Note: agent_context fixture comes from tests/unit_tests/agent/conftest.py
    """
    with patch('autobyteus.agent.runtime.agent_worker.WorkerEventDispatcher', return_value=mock_dispatcher):
        dummy_registry = MagicMock(spec=EventHandlerRegistry)
        worker = AgentWorker(context=agent_context, event_handler_registry=dummy_registry)
        yield worker
        # Ensure worker is stopped after test if it was started
        asyncio.run(worker.stop())

@pytest.mark.asyncio
async def test_worker_initialization(agent_worker, agent_context, mock_dispatcher):
    """Test that the worker initializes correctly."""
    assert agent_worker.context is agent_context
    assert agent_worker.worker_event_dispatcher is mock_dispatcher
    assert not agent_worker.is_alive()
    assert agent_worker.status_manager is agent_context.status_manager

@pytest.mark.asyncio
async def test_worker_start_and_stop_cycle(agent_worker):
    """Test the basic start and stop lifecycle of the worker."""
    assert not agent_worker.is_alive()
    
    worker_completed_future = asyncio.Future()
    def on_done(future):
        worker_completed_future.set_result(True)

    agent_worker.add_done_callback(on_done)
    
    with patch.object(agent_worker, '_initialize', return_value=True):
        agent_worker.start()
        await asyncio.sleep(0.1) # Give worker time to start
        assert agent_worker.is_alive()
        assert agent_worker.get_worker_loop() is not None

    await agent_worker.stop(timeout=2.0)
    
    await asyncio.wait_for(worker_completed_future, timeout=1.0)

    assert not agent_worker.is_alive()
    # The loop is closed internally, so get_worker_loop should now return None
    assert agent_worker.get_worker_loop() is None 
    assert agent_worker._thread_future.done()

@pytest.mark.asyncio
async def test_initialize_delegates_to_bootstrapper_success(agent_worker, agent_context):
    """Test that _initialize successfully delegates to AgentBootstrapper."""
    mock_bootstrapper_instance = AsyncMock(spec=AgentBootstrapper)
    mock_bootstrapper_instance.run.return_value = True

    with patch('autobyteus.agent.runtime.agent_worker.AgentBootstrapper', return_value=mock_bootstrapper_instance) as mock_bootstrapper_class:
        success = await agent_worker._initialize()

        assert success is True
        mock_bootstrapper_class.assert_called_once_with() # Check it's initialized
        mock_bootstrapper_instance.run.assert_awaited_once_with(agent_context, agent_context.status_manager)

@pytest.mark.asyncio
async def test_initialize_delegates_to_bootstrapper_failure(agent_worker, agent_context):
    """Test that _initialize handles failure from AgentBootstrapper."""
    mock_bootstrapper_instance = AsyncMock(spec=AgentBootstrapper)
    mock_bootstrapper_instance.run.return_value = False # Simulate failure

    with patch('autobyteus.agent.runtime.agent_worker.AgentBootstrapper', return_value=mock_bootstrapper_instance) as mock_bootstrapper_class:
        success = await agent_worker._initialize()

        assert success is False
        mock_bootstrapper_class.assert_called_once_with()
        mock_bootstrapper_instance.run.assert_awaited_once_with(agent_context, agent_context.status_manager)

@pytest.mark.asyncio
async def test_worker_processes_event(agent_worker, agent_context, mock_dispatcher):
    """Test that the worker can process an event from its queue."""
    # Mock the initialization to succeed
    
    # Avoid using asyncio.Queue across loops. Use a safe side_effect.
    test_event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    
    async def safe_side_effect():
        if not hasattr(safe_side_effect, 'yielded'):
            safe_side_effect.yielded = True
            return ("user_message_input_queue", test_event)
        # Keep worker alive but idle
        await asyncio.sleep(0.5)
        return None

    agent_context.state.input_event_queues.get_next_input_event.side_effect = safe_side_effect
    
    with patch.object(agent_worker, '_initialize', return_value=True):
        agent_worker.start()
        await asyncio.sleep(0.2) # Give worker time to process initial event
        assert agent_worker.is_alive()

        # The dispatcher should have been called by now
        mock_dispatcher.dispatch.assert_awaited_with(test_event, agent_context)

        await agent_worker.stop()

@pytest.mark.asyncio
async def test_worker_handles_dispatcher_exception(agent_worker, agent_context, mock_dispatcher):
    """Test that an exception from the dispatcher is caught and handled."""
    
    test_event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    error_message = "Dispatcher failed!"
    mock_dispatcher.dispatch.side_effect = ValueError(error_message)

    async def safe_side_effect():
        if not hasattr(safe_side_effect, 'yielded'):
            safe_side_effect.yielded = True
            return ("user_message_input_queue", test_event)
        await asyncio.sleep(0.5)
        return None

    agent_context.state.input_event_queues.get_next_input_event.side_effect = safe_side_effect
    
    with patch.object(agent_worker, '_initialize', return_value=True):
        agent_worker.start()
        await asyncio.sleep(0.2)
        assert agent_worker.is_alive()

        # The dispatcher now handles notifying error, so we check that.
        agent_context.status_manager.notify_error_occurred.assert_awaited_once()

        await agent_worker.stop()
