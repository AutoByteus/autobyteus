# file: autobyteus/tests/unit_tests/agent_team/runtime/test_agent_team_worker.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager
from autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper import AgentTeamBootstrapper
from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
from autobyteus.agent_team.events.agent_team_event_dispatcher import AgentTeamEventDispatcher
from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent
from autobyteus.agent_team.handlers.agent_team_event_handler_registry import AgentTeamEventHandlerRegistry
from autobyteus.agent_team.runtime.agent_team_worker import AgentTeamWorker
from autobyteus.agent_team.shutdown_steps.agent_team_shutdown_orchestrator import AgentTeamShutdownOrchestrator

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
def mock_agent_team_dispatcher():
    """Provides a mock AgentTeamEventDispatcher."""
    return AsyncMock(spec=AgentTeamEventDispatcher)

@pytest.fixture
def agent_team_worker(agent_team_context: AgentTeamContext, mock_agent_team_dispatcher: AsyncMock):
    """
    Provides a AgentTeamWorker instance with a mocked dispatcher.
    """
    with patch('autobyteus.agent_team.runtime.agent_team_worker.AgentTeamEventDispatcher', return_value=mock_agent_team_dispatcher):
        dummy_registry = MagicMock(spec=AgentTeamEventHandlerRegistry)
        worker = AgentTeamWorker(context=agent_team_context, event_handler_registry=dummy_registry)
        yield worker
        # Ensure worker is stopped after test if it was started
        if worker.is_alive:
            asyncio.run(worker.stop())

@pytest.mark.asyncio
async def test_worker_initialization(agent_team_worker: AgentTeamWorker, agent_team_context: AgentTeamContext, mock_agent_team_dispatcher: AsyncMock):
    """Test that the worker initializes correctly."""
    assert agent_team_worker.context is agent_team_context
    assert agent_team_worker.event_dispatcher is mock_agent_team_dispatcher
    assert not agent_team_worker.is_alive
    assert agent_team_worker.phase_manager is agent_team_context.phase_manager

@pytest.mark.asyncio
async def test_worker_start_and_stop_cycle(agent_team_worker: AgentTeamWorker):
    """Test the basic start and stop lifecycle of the worker."""
    assert not agent_team_worker.is_alive

    worker_completed_future = asyncio.Future()
    def on_done(future):
        worker_completed_future.set_result(True)

    agent_team_worker.add_done_callback(on_done)
    
    with patch('autobyteus.agent_team.runtime.agent_team_worker.AgentTeamBootstrapper') as MockBootstrapper:
        MockBootstrapper.return_value.run = AsyncMock(return_value=True) # Simulate successful bootstrap
        
        agent_team_worker.start()
        await asyncio.sleep(0.1) # Give worker time to start
        assert agent_team_worker.is_alive
        assert agent_team_worker.get_worker_loop() is not None

    await agent_team_worker.stop(timeout=2.0)
    
    await asyncio.wait_for(worker_completed_future, timeout=1.0)

    assert not agent_team_worker.is_alive
    assert agent_team_worker.get_worker_loop() is None 
    assert agent_team_worker._thread_future.done()

@pytest.mark.asyncio
async def test_async_run_initialization_delegates_to_bootstrapper(agent_team_worker: AgentTeamWorker, agent_team_context: AgentTeamContext):
    """Test that async_run successfully delegates to AgentTeamBootstrapper."""
    mock_bootstrapper_instance = AsyncMock(spec=AgentTeamBootstrapper)
    mock_bootstrapper_instance.run.return_value = True

    # We only test the initialization part, so we'll stop the loop right after.
    agent_team_worker._async_stop_event = asyncio.Event()
    agent_team_worker._async_stop_event.set()

    with patch('autobyteus.agent_team.runtime.agent_team_worker.AgentTeamBootstrapper', return_value=mock_bootstrapper_instance) as mock_bootstrapper_class:
        await agent_team_worker.async_run()

        mock_bootstrapper_class.assert_called_once_with()
        mock_bootstrapper_instance.run.assert_awaited_once_with(agent_team_context, agent_team_context.phase_manager)

@pytest.mark.asyncio
async def test_async_run_handles_bootstrap_failure(agent_team_worker: AgentTeamWorker, agent_team_context: AgentTeamContext):
    """Test that async_run handles failure from AgentTeamBootstrapper and exits."""
    mock_bootstrapper_instance = AsyncMock(spec=AgentTeamBootstrapper)
    mock_bootstrapper_instance.run.return_value = False # Simulate failure

    with patch('autobyteus.agent_team.runtime.agent_team_worker.AgentTeamBootstrapper', return_value=mock_bootstrapper_instance) as mock_bootstrapper_class:
        await agent_team_worker.async_run()

        mock_bootstrapper_class.assert_called_once()
        mock_bootstrapper_instance.run.assert_awaited_once_with(agent_team_context, agent_team_context.phase_manager)
        # The event loop should not have been entered, so no calls to get events.
        agent_team_context.state.input_event_queues.user_message_queue.get.assert_not_called()

@pytest.mark.asyncio
async def test_worker_processes_event(agent_team_worker: AgentTeamWorker, agent_team_context: AgentTeamContext, mock_agent_team_dispatcher: AsyncMock):
    """Test that the worker can process an event from its queue."""
    with patch('autobyteus.agent_team.runtime.agent_team_worker.AgentTeamBootstrapper') as MockBootstrapper:
        MockBootstrapper.return_value.run.return_value = True
        
        agent_team_worker.start()
        await asyncio.sleep(0.1) # Give worker time to start up
        assert agent_team_worker.is_alive

        test_event = ProcessUserMessageEvent(user_message=MagicMock(), target_agent_name="Coordinator")
        
        await agent_team_context.state.input_event_queues.user_message_queue.put(test_event)
        
        await asyncio.sleep(0.2)
        
        mock_agent_team_dispatcher.dispatch.assert_awaited_with(test_event, agent_team_context)

        await agent_team_worker.stop()

@pytest.mark.asyncio
async def test_worker_shutdown_delegates_to_orchestrator(agent_team_worker: AgentTeamWorker):
    """Test that the shutdown sequence delegates to the AgentTeamShutdownOrchestrator."""
    mock_shutdown_orchestrator = AsyncMock(spec=AgentTeamShutdownOrchestrator)
    
    with patch('autobyteus.agent_team.runtime.agent_team_worker.AgentTeamShutdownOrchestrator', return_value=mock_shutdown_orchestrator):
        with patch('autobyteus.agent_team.runtime.agent_team_worker.AgentTeamBootstrapper') as MockBootstrapper:
            MockBootstrapper.return_value.run.return_value = True
            
            agent_team_worker.start()
            await asyncio.sleep(0.1)
            
            await agent_team_worker.stop()

    mock_shutdown_orchestrator.run.assert_awaited_once_with(agent_team_worker.context)
