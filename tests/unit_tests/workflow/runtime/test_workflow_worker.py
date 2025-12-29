import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager
from autobyteus.workflow.bootstrap_steps.workflow_bootstrapper import WorkflowBootstrapper
from autobyteus.workflow.context.workflow_context import WorkflowContext
from autobyteus.workflow.events.workflow_event_dispatcher import WorkflowEventDispatcher
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent
from autobyteus.workflow.handlers.workflow_event_handler_registry import WorkflowEventHandlerRegistry
from autobyteus.workflow.runtime.workflow_worker import WorkflowWorker
from autobyteus.workflow.shutdown_steps.workflow_shutdown_orchestrator import WorkflowShutdownOrchestrator

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
def mock_workflow_dispatcher():
    """Provides a mock WorkflowEventDispatcher."""
    return AsyncMock(spec=WorkflowEventDispatcher)

@pytest.fixture
def workflow_worker(workflow_context: WorkflowContext, mock_workflow_dispatcher: AsyncMock):
    """
    Provides a WorkflowWorker instance with a mocked dispatcher.
    Note: workflow_context fixture comes from tests/unit_tests/workflow/conftest.py
    """
    with patch('autobyteus.workflow.runtime.workflow_worker.WorkflowEventDispatcher', return_value=mock_workflow_dispatcher):
        dummy_registry = MagicMock(spec=WorkflowEventHandlerRegistry)
        worker = WorkflowWorker(context=workflow_context, event_handler_registry=dummy_registry)
        yield worker
        # Ensure worker is stopped after test if it was started
        if worker.is_alive:
            asyncio.run(worker.stop())

@pytest.mark.asyncio
async def test_worker_initialization(workflow_worker: WorkflowWorker, workflow_context: WorkflowContext, mock_workflow_dispatcher: AsyncMock):
    """Test that the worker initializes correctly."""
    assert workflow_worker.context is workflow_context
    assert workflow_worker.event_dispatcher is mock_workflow_dispatcher
    assert not workflow_worker.is_alive
    assert workflow_worker.status_manager is workflow_context.status_manager

@pytest.mark.asyncio
async def test_worker_start_and_stop_cycle(workflow_worker: WorkflowWorker):
    """Test the basic start and stop lifecycle of the worker."""
    assert not workflow_worker.is_alive

    worker_completed_future = asyncio.Future()
    def on_done(future):
        worker_completed_future.set_result(True)

    workflow_worker.add_done_callback(on_done)
    
    with patch('autobyteus.workflow.runtime.workflow_worker.WorkflowBootstrapper') as MockBootstrapper:
        # FIX: The `run` method is an `async` method. The mock must be an `AsyncMock`
        # so that it returns an awaitable (a coroutine) that resolves to `True`.
        # The previous `return_value = True` caused `await True`, which is a TypeError.
        MockBootstrapper.return_value.run = AsyncMock(return_value=True) # Simulate successful bootstrap
        
        workflow_worker.start()
        await asyncio.sleep(0.1) # Give worker time to start
        assert workflow_worker.is_alive
        assert workflow_worker.get_worker_loop() is not None

    await workflow_worker.stop(timeout=2.0)
    
    await asyncio.wait_for(worker_completed_future, timeout=1.0)

    assert not workflow_worker.is_alive
    assert workflow_worker.get_worker_loop() is None 
    assert workflow_worker._thread_future.done()

@pytest.mark.asyncio
async def test_async_run_initialization_delegates_to_bootstrapper(workflow_worker: WorkflowWorker, workflow_context: WorkflowContext):
    """Test that async_run successfully delegates to WorkflowBootstrapper."""
    mock_bootstrapper_instance = AsyncMock(spec=WorkflowBootstrapper)
    mock_bootstrapper_instance.run.return_value = True

    # We only test the initialization part, so we'll stop the loop right after.
    workflow_worker._async_stop_event = asyncio.Event()
    workflow_worker._async_stop_event.set()

    with patch('autobyteus.workflow.runtime.workflow_worker.WorkflowBootstrapper', return_value=mock_bootstrapper_instance) as mock_bootstrapper_class:
        await workflow_worker.async_run()

        mock_bootstrapper_class.assert_called_once_with()
        mock_bootstrapper_instance.run.assert_awaited_once_with(workflow_context, workflow_context.status_manager)

@pytest.mark.asyncio
async def test_async_run_handles_bootstrap_failure(workflow_worker: WorkflowWorker, workflow_context: WorkflowContext):
    """Test that async_run handles failure from WorkflowBootstrapper and exits."""
    mock_bootstrapper_instance = AsyncMock(spec=WorkflowBootstrapper)
    mock_bootstrapper_instance.run.return_value = False # Simulate failure

    with patch('autobyteus.workflow.runtime.workflow_worker.WorkflowBootstrapper', return_value=mock_bootstrapper_instance) as mock_bootstrapper_class:
        await workflow_worker.async_run()

        mock_bootstrapper_class.assert_called_once()
        mock_bootstrapper_instance.run.assert_awaited_once_with(workflow_context, workflow_context.status_manager)
        # The event loop should not have been entered, so no calls to get events.
        workflow_context.state.input_event_queues.user_message_queue.get.assert_not_called()

@pytest.mark.asyncio
async def test_worker_processes_event(workflow_worker: WorkflowWorker, workflow_context: WorkflowContext, mock_workflow_dispatcher: AsyncMock):
    """Test that the worker can process an event from its queue."""
    # Mock the bootstrapper to succeed
    with patch('autobyteus.workflow.runtime.workflow_worker.WorkflowBootstrapper') as MockBootstrapper:
        MockBootstrapper.return_value.run.return_value = True
        
        # Start the worker thread
        workflow_worker.start()
        await asyncio.sleep(0.1) # Give worker time to start up
        assert workflow_worker.is_alive

        test_event = ProcessUserMessageEvent(user_message=MagicMock(), target_agent_name="Coordinator")
        
        # Put the event onto the queue to unblock the worker's main loop
        await workflow_context.state.input_event_queues.user_message_queue.put(test_event)
        
        # Give the worker time to process the event
        await asyncio.sleep(0.2)
        
        # Verify the dispatcher was called with the event
        mock_workflow_dispatcher.dispatch.assert_awaited_with(test_event, workflow_context)

        await workflow_worker.stop()

@pytest.mark.asyncio
async def test_worker_shutdown_delegates_to_orchestrator(workflow_worker: WorkflowWorker):
    """Test that the shutdown sequence delegates to the WorkflowShutdownOrchestrator."""
    mock_shutdown_orchestrator = AsyncMock(spec=WorkflowShutdownOrchestrator)
    
    with patch('autobyteus.workflow.runtime.workflow_worker.WorkflowShutdownOrchestrator', return_value=mock_shutdown_orchestrator):
        with patch('autobyteus.workflow.runtime.workflow_worker.WorkflowBootstrapper') as MockBootstrapper:
            MockBootstrapper.return_value.run.return_value = True
            
            workflow_worker.start()
            await asyncio.sleep(0.1)
            
            await workflow_worker.stop()

    mock_shutdown_orchestrator.run.assert_awaited_once_with(workflow_worker.context)
