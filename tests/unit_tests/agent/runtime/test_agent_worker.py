# file: autobyteus/tests/unit_tests/agent/runtime/test_agent_worker.py
import asyncio
import pytest
import concurrent.futures
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.runtime.agent_worker import AgentWorker
from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager
from autobyteus.agent.context import AgentContext, AgentConfig, AgentRuntimeState, AgentPhaseManager
from autobyteus.agent.events import AgentInputEventQueueManager, WorkerEventDispatcher
from autobyteus.agent.events.agent_events import (
    UserMessageReceivedEvent, AgentErrorEvent, AgentStoppedEvent, BaseEvent
)
from autobyteus.agent.handlers import EventHandlerRegistry
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.context.phases import AgentOperationalPhase

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

# A simplified agent_context fixture for worker tests
@pytest.fixture
def agent_context():
    """Provides a basic AgentContext suitable for worker tests."""
    agent_id = "test-worker-agent"
    definition = AgentDefinition(
        name="TestWorkerDef", role="Tester", description="Test",
        system_prompt="Test", tool_names=[]
    )
    agent_config = AgentConfig(agent_id=agent_id, definition=definition, auto_execute_tools=True, llm_model_name="mock_model")
    runtime_state = AgentRuntimeState(agent_id=agent_id)
    context = AgentContext(config=agent_config, state=runtime_state)
    
    notifier = AgentExternalEventNotifier(agent_id=agent_id)
    phase_manager = AgentPhaseManager(context=context, notifier=notifier)
    context.state.phase_manager_ref = phase_manager
    
    return context

@pytest.fixture
def mock_dispatcher():
    """Provides a mock WorkerEventDispatcher."""
    return AsyncMock(spec=WorkerEventDispatcher)

@pytest.fixture
def agent_worker(agent_context, mock_dispatcher):
    """
    Provides an AgentWorker instance with a mocked dispatcher.
    """
    with patch('autobyteus.agent.runtime.agent_worker.WorkerEventDispatcher', return_value=mock_dispatcher):
        dummy_registry = MagicMock(spec=EventHandlerRegistry)
        worker = AgentWorker(context=agent_context, event_handler_registry=dummy_registry)
        yield worker

@pytest.mark.asyncio
async def test_worker_initialization(agent_worker, agent_context, mock_dispatcher):
    """Test that the worker initializes correctly."""
    assert agent_worker.context is agent_context
    assert agent_worker.worker_event_dispatcher is mock_dispatcher
    assert not agent_worker.is_alive()
    assert agent_worker.phase_manager is agent_context.phase_manager

@pytest.mark.asyncio
async def test_worker_start_and_stop_cycle(agent_worker):
    """Test the basic start and stop lifecycle of the worker."""
    assert not agent_worker.is_alive()
    
    worker_started = asyncio.Event()
    def on_done(future):
        worker_started.set()

    agent_worker.add_done_callback(on_done)
    agent_worker.start()

    await asyncio.sleep(0.1)
    assert agent_worker.is_alive()
    assert agent_worker.get_worker_loop() is not None
    
    await agent_worker.stop(timeout=2.0)
    
    await asyncio.wait_for(worker_started.wait(), timeout=1.0)

    assert not agent_worker.is_alive()
    assert agent_worker.get_worker_loop() is None
    assert agent_worker._thread_future.done()

@pytest.mark.asyncio
async def test_worker_processes_event_after_queues_are_set(agent_worker, agent_context, mock_dispatcher):
    """Test that the worker can process an event after its queues are initialized."""
    
    agent_worker.start()
    await asyncio.sleep(0.1) # Give worker time to start
    assert agent_worker.is_alive()

    # Prepare the mock queue manager
    mock_queue_manager = AsyncMock(spec=AgentInputEventQueueManager)
    test_event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    
    # Use a side effect function for more controlled behavior
    _event_yielded = False
    async def mock_get_next_event(*args, **kwargs):
        nonlocal _event_yielded
        if not _event_yielded:
            _event_yielded = True
            return "user_message_input_queue", test_event
        else:
            # Simulate an empty queue by hanging, which will cause the
            # worker's wait_for to timeout, as expected.
            await asyncio.sleep(1) 
            return None

    mock_queue_manager.get_next_input_event.side_effect = mock_get_next_event
    
    # Inject the mock queue manager into the running worker's context
    agent_context.state.input_event_queues = mock_queue_manager
    
    # Give the worker loop time to process the event
    await asyncio.sleep(0.2)
    
    # Now, assert that the dispatcher was called with the event
    mock_dispatcher.dispatch.assert_awaited_with(test_event, agent_context)

    await agent_worker.stop()

@pytest.mark.asyncio
async def test_worker_handles_dispatcher_exception(agent_worker, agent_context, mock_dispatcher):
    """Test that an exception from the dispatcher is caught and handled."""
    agent_worker.start()
    await asyncio.sleep(0.1)

    mock_queue_manager = AsyncMock(spec=AgentInputEventQueueManager)
    test_event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    
    # Use a robust side effect to avoid hot loops and provide the event once
    _event_yielded = False
    async def mock_get_next_event(*args, **kwargs):
        nonlocal _event_yielded
        if not _event_yielded:
            _event_yielded = True
            return "user_message_input_queue", test_event
        else:
            await asyncio.sleep(1)
            return None
            
    mock_queue_manager.get_next_input_event.side_effect = mock_get_next_event
    agent_context.state.input_event_queues = mock_queue_manager
    mock_queue_manager.enqueue_internal_system_event = AsyncMock() # Need to mock this method

    error_message = "Dispatcher failed!"
    mock_dispatcher.dispatch.side_effect = ValueError(error_message)

    await asyncio.sleep(0.2)
    
    # Assertions remain the same
    agent_context.phase_manager.notify_error_occurred.assert_called_once()
    args, _ = agent_context.phase_manager.notify_error_occurred.call_args
    assert error_message in args[0]
    assert "Traceback" in args[1]
    
    mock_queue_manager.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = mock_queue_manager.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert error_message in enqueued_event.error_message

    await agent_worker.stop()

@pytest.mark.asyncio
async def test_worker_stops_on_stop_event(agent_worker):
    """Test that the worker's async_run loop exits when the stop event is set."""
    agent_worker.start()
    await asyncio.sleep(0.1)
    
    assert agent_worker._async_stop_event is not None
    agent_worker._async_stop_event.set()

    try:
        await asyncio.wait_for(asyncio.wrap_future(agent_worker._thread_future), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Worker thread did not terminate after _async_stop_event was set.")

    assert agent_worker._thread_future.done()

@pytest.mark.asyncio
async def test_worker_start_idempotency(agent_worker, module_scoped_thread_pool_manager):
    """Test that calling start() multiple times has no adverse effect."""
    thread_pool_manager = module_scoped_thread_pool_manager
    
    with patch.object(thread_pool_manager, 'submit_task', wraps=thread_pool_manager.submit_task) as mock_submit:
        agent_worker.start()
        await asyncio.sleep(0.1)
        first_future = agent_worker._thread_future
        mock_submit.assert_called_once()

        agent_worker.start()
        await asyncio.sleep(0.05)
        assert agent_worker._thread_future is first_future
        mock_submit.assert_called_once()

    await agent_worker.stop()

@pytest.mark.asyncio
async def test_worker_stop_idempotency(agent_worker):
    """Test that calling stop() multiple times is safe."""
    agent_worker.start()
    await asyncio.sleep(0.1)
    await agent_worker.stop()
    
    # Check that calling stop again does not cause issues and is a no-op
    with patch.object(agent_worker, '_signal_internal_stop', new_callable=AsyncMock) as mock_signal:
        await agent_worker.stop()
        mock_signal.assert_not_called()

    assert not agent_worker.is_alive()
