# file: autobyteus/tests/unit_tests/agent/test_agent_runtime.py
import asyncio
import pytest
import logging 
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from autobyteus.agent.agent_runtime import AgentRuntime
from autobyteus.agent.context import AgentContext, AgentStatusManager
from autobyteus.agent.events import (
    AgentEventQueues,
    BaseEvent,
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    UserMessageReceivedEvent, 
    AgentProcessingEvent, # Base for operational/preparation events
    AgentOperationalEvent, # For status change logic
    CreateToolInstancesEvent # Initial event in the loop
)
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.status import AgentStatus
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.agent.registry.agent_definition import AgentDefinition 
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage 
from autobyteus.events.event_emitter import EventEmitter 


@pytest.fixture
def mock_agent_definition():
    return AgentDefinition(
        name="TestAgent",
        role="tester",
        description="A test agent definition",
        system_prompt="You are a test agent.",
        tool_names=[]
    )

@pytest.fixture
def mock_llm_instance():
    llm = MagicMock(spec=BaseLLM)
    llm.cleanup = AsyncMock()
    return llm

@pytest.fixture
def mock_event_queues():
    queues = MagicMock(spec=AgentEventQueues)
    queues.get_next_input_event = AsyncMock(return_value=None) 
    queues.enqueue_internal_system_event = AsyncMock()
    queues.graceful_shutdown = AsyncMock()
    queues.enqueue_end_of_stream_sentinel_to_output_queue = AsyncMock()
    # Simulate structure for all(q.empty() for _, q in self.context.queues._input_queues)
    mock_single_q = MagicMock(spec=asyncio.Queue)
    mock_single_q.empty = MagicMock(return_value=True)
    queues._input_queues = [("mock_q", mock_single_q)]
    return queues

@pytest.fixture
def mock_agent_context(mock_agent_definition, mock_event_queues, mock_llm_instance):
    context = MagicMock(spec=AgentContext)
    context.agent_id = "test_agent_123"
    context.definition = mock_agent_definition
    context.queues = mock_event_queues
    context.llm_instance = mock_llm_instance # Property will access state.llm_instance
    context.status = AgentStatus.NOT_STARTED # Property will access state.status
    
    # Mock property setters/getters if direct assignment to properties is problematic
    # For 'status', AgentStatusManager sets it on context.state.status.
    # So, we'll let AgentStatusManager initialize it, or set it via status_manager in tests.
    # For 'llm_instance', runtime would set context.state.llm_instance.
    # For tests, direct assignment to context.llm_instance should work if property setter is simple.
    
    # To allow AgentStatusManager to set context.status correctly via property:
    # context.state = MagicMock() # Ensure state object exists for status_manager
    # context.state.status = AgentStatus.NOT_STARTED # Initial state for status_manager
    # Let AgentRuntime's __init__ create the AgentStatusManager, which will set this.
    return context

@pytest.fixture
def mock_event_handler_registry():
    registry = MagicMock(spec=EventHandlerRegistry)
    registry.get_handler = MagicMock(return_value=None) 
    return registry

@pytest.fixture
def agent_runtime(mock_agent_context, mock_event_handler_registry):
    # AgentRuntime constructor will create AgentStatusManager, which sets initial status on context
    runtime = AgentRuntime(context=mock_agent_context, event_handler_registry=mock_event_handler_registry)
    return runtime


@pytest.mark.asyncio
async def test_initialization(agent_runtime: AgentRuntime, mock_agent_context, mock_event_handler_registry):
    assert agent_runtime.context == mock_agent_context
    assert agent_runtime.event_handler_registry == mock_event_handler_registry
    assert isinstance(agent_runtime.status_manager, AgentStatusManager)
    assert isinstance(agent_runtime.status_manager, EventEmitter) # AgentStatusManager is an EventEmitter
    assert not isinstance(agent_runtime, EventEmitter) # AgentRuntime itself is not
    assert agent_runtime.status_manager.context == mock_agent_context
    
    # AgentStatusManager constructor sets the initial status on the context
    assert agent_runtime.context.status == AgentStatus.NOT_STARTED 
    assert not agent_runtime._is_running_flag
    assert agent_runtime._main_loop_task is None

@pytest.mark.asyncio
async def test_start_execution_loop(agent_runtime: AgentRuntime):
    mock_task_instance = AsyncMock(spec=asyncio.Task) 
    mock_task_instance.done.return_value = False      

    with patch('asyncio.create_task', return_value=mock_task_instance) as mock_create_task, \
         patch.object(agent_runtime.status_manager, 'notify_runtime_starting') as mock_notify_starting, \
         patch.object(agent_runtime.context.queues, 'enqueue_internal_system_event', new_callable=AsyncMock) as mock_enqueue_init_event:

        agent_runtime.start_execution_loop() 

        assert agent_runtime._is_running_flag
        assert not agent_runtime._stop_requested.is_set()
        mock_notify_starting.assert_called_once()
        mock_create_task.assert_called_once_with(ANY, name=f"agent_runtime_loop_{agent_runtime.context.agent_id}")
        assert agent_runtime._main_loop_task == mock_task_instance
        
        # Assert that CreateToolInstancesEvent is enqueued by _execution_loop start logic (now inside start_execution_loop indirectly)
        # _execution_loop itself enqueues it.
        # This check becomes tricky as _execution_loop is a separate task.
        # We can check if it was called after a short sleep.
        await asyncio.sleep(0.01) # Give loop a chance to start and enqueue
        
        found_init_event = False
        for call in mock_enqueue_init_event.call_args_list:
            if isinstance(call.args[0], CreateToolInstancesEvent):
                found_init_event = True
                break
        assert found_init_event, "CreateToolInstancesEvent was not enqueued by the start of _execution_loop."

        # Test idempotency
        mock_notify_starting.reset_mock()
        mock_create_task.reset_mock()
        mock_enqueue_init_event.reset_mock() # Reset for idempotency check
        
        agent_runtime.start_execution_loop() # Call start again
        
        mock_notify_starting.assert_not_called() 
        mock_create_task.assert_not_called()
        mock_enqueue_init_event.assert_not_called() # Should not enqueue init event again if already running

    # Cleanup for test state
    if agent_runtime._main_loop_task is mock_task_instance: 
        mock_task_instance.done.return_value = True 
        if not mock_task_instance.cancelled(): # Avoid awaiting if already cancelled
             try:
                 await asyncio.wait_for(mock_task_instance, timeout=0.01)
             except (asyncio.TimeoutError, asyncio.CancelledError):
                 pass # Expected if it was running
    agent_runtime._is_running_flag = False 
    agent_runtime._main_loop_task = None 


@pytest.mark.asyncio
async def test_stop_execution_loop_when_not_running(agent_runtime: AgentRuntime):
    agent_runtime._is_running_flag = False
    agent_runtime._main_loop_task = None
    
    with patch.object(agent_runtime.status_manager, 'notify_final_shutdown_complete') as mock_notify_final, \
         patch.object(agent_runtime.context.queues, 'graceful_shutdown', new_callable=AsyncMock) as mock_q_shutdown, \
         patch.object(agent_runtime.context.llm_instance, 'cleanup', new_callable=AsyncMock) as mock_llm_cleanup:

        await agent_runtime.stop_execution_loop()
        mock_notify_final.assert_not_called() 
        mock_q_shutdown.assert_not_called()
        mock_llm_cleanup.assert_not_called()

@pytest.mark.asyncio
async def test_stop_execution_loop_graceful(agent_runtime: AgentRuntime):
    agent_runtime._is_running_flag = True
    mock_task = AsyncMock(spec=asyncio.Task)
    mock_task.done.return_value = False
    agent_runtime._main_loop_task = mock_task
    
    with patch.object(agent_runtime.status_manager, 'notify_final_shutdown_complete') as mock_notify_final, \
         patch.object(agent_runtime.context.queues, 'enqueue_internal_system_event', new_callable=AsyncMock) as mock_enqueue_stop, \
         patch.object(agent_runtime.context.queues, 'graceful_shutdown', new_callable=AsyncMock) as mock_q_shutdown, \
         patch.object(agent_runtime.context.llm_instance, 'cleanup', new_callable=AsyncMock) as mock_llm_cleanup, \
         patch('asyncio.wait_for', new_callable=AsyncMock) as mock_wait_for:

        await agent_runtime.stop_execution_loop(timeout=0.1)

        assert agent_runtime._stop_requested.is_set()
        mock_enqueue_stop.assert_called_once_with(ANY) 
        assert isinstance(mock_enqueue_stop.call_args[0][0], AgentStoppedEvent)
        
        mock_wait_for.assert_called_once_with(mock_task, timeout=0.1)
        
        mock_q_shutdown.assert_called_once_with(timeout=ANY)
        mock_llm_cleanup.assert_called_once() # Assert LLM cleanup
        mock_notify_final.assert_called_once()
        assert not agent_runtime._is_running_flag
        assert agent_runtime._main_loop_task is None

@pytest.mark.asyncio
async def test_stop_execution_loop_timeout(agent_runtime: AgentRuntime):
    agent_runtime._is_running_flag = True
    mock_task = AsyncMock(spec=asyncio.Task)
    mock_task.done.return_value = False
    mock_task.cancel = MagicMock() 
    agent_runtime._main_loop_task = mock_task

    with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError) as mock_wait_for, \
         patch.object(agent_runtime.status_manager, 'notify_final_shutdown_complete') as mock_notify_final, \
         patch.object(agent_runtime.context.queues, 'graceful_shutdown', new_callable=AsyncMock) as mock_q_shutdown, \
         patch.object(agent_runtime.context.llm_instance, 'cleanup', new_callable=AsyncMock) as mock_llm_cleanup:

        await agent_runtime.stop_execution_loop(timeout=0.01)

        mock_wait_for.assert_called_once_with(mock_task, timeout=0.01)
        mock_task.cancel.assert_called_once() 
        mock_q_shutdown.assert_called_once()
        mock_llm_cleanup.assert_called_once() # Assert LLM cleanup
        mock_notify_final.assert_called_once()
        assert not agent_runtime._is_running_flag

@pytest.mark.asyncio
async def test_dispatch_event_with_handler(agent_runtime: AgentRuntime, mock_agent_context):
    mock_handler = MagicMock()
    mock_handler.handle = AsyncMock()
    agent_runtime.event_handler_registry.get_handler.return_value = mock_handler
    
    test_event = AgentStartedEvent() 
    
    with patch.object(agent_runtime.status_manager, 'notify_agent_started_event_handled') as mock_notify_started_handled:
        await agent_runtime._dispatch_event(test_event)

        agent_runtime.event_handler_registry.get_handler.assert_called_once_with(AgentStartedEvent)
        mock_handler.handle.assert_called_once_with(test_event, mock_agent_context)
        mock_notify_started_handled.assert_called_once() # This is called if event is AgentStartedEvent

@pytest.mark.asyncio
async def test_dispatch_event_handler_exception(agent_runtime: AgentRuntime, mock_agent_context):
    mock_handler = MagicMock()
    mock_handler.handle = AsyncMock(side_effect=ValueError("Handler error"))
    agent_runtime.event_handler_registry.get_handler.return_value = mock_handler
    
    test_event = UserMessageReceivedEvent(agent_input_user_message=AgentInputUserMessage(content="test"))
    
    with patch.object(agent_runtime.status_manager, 'notify_error_occurred') as mock_notify_error, \
         patch.object(mock_agent_context.queues, 'enqueue_internal_system_event', new_callable=AsyncMock) as mock_enqueue_error:

        await agent_runtime._dispatch_event(test_event)

        mock_handler.handle.assert_called_once()
        mock_notify_error.assert_called_once()
        mock_enqueue_error.assert_called_once()
        error_event_arg = mock_enqueue_error.call_args[0][0]
        assert isinstance(error_event_arg, AgentErrorEvent)
        assert "Handler error" in error_event_arg.error_message

@pytest.mark.asyncio
async def test_dispatch_event_no_handler(agent_runtime: AgentRuntime, mock_agent_context, caplog):
    agent_runtime.event_handler_registry.get_handler.return_value = None 
    class UnknownEvent(BaseEvent): pass 
    test_event = UnknownEvent()

    with caplog.at_level(logging.WARNING): # Ensure caplog captures WARNING level
        await agent_runtime._dispatch_event(test_event)
    
    # Check for the specific warning message
    assert f"Agent '{mock_agent_context.agent_id}' _dispatch_event: No handler for '{type(test_event).__name__}'." in caplog.text

@pytest.mark.asyncio
async def test_status_property(agent_runtime: AgentRuntime, mock_agent_context):
    # AgentStatusManager sets status on context.state.status, which context.status property reads
    # agent_runtime.context.status is mocked, so we can set its return_value
    mock_agent_context.status = AgentStatus.RUNNING # Simulate status being set
    assert agent_runtime.status == AgentStatus.RUNNING
    
    mock_agent_context.status = None # Simulate status being None
    with patch.object(logging.getLogger('autobyteus.agent.agent_runtime'), 'error') as mock_log_error:
        agent_runtime._is_running_flag = True # To test the ERROR branch
        assert agent_runtime.status == AgentStatus.ERROR
        mock_log_error.assert_called_once_with(
             f"AgentRuntime '{mock_agent_context.agent_id}': context.status is None. Defaulting to NOT_STARTED/ERROR."
        )
        mock_log_error.reset_mock()
        agent_runtime._is_running_flag = False # To test the NOT_STARTED branch
        assert agent_runtime.status == AgentStatus.NOT_STARTED
        mock_log_error.assert_called_once_with(
             f"AgentRuntime '{mock_agent_context.agent_id}': context.status is None. Defaulting to NOT_STARTED/ERROR."
        )

@pytest.mark.asyncio
async def test_is_running_property(agent_runtime: AgentRuntime): 
    agent_runtime._is_running_flag = True
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False
    agent_runtime._main_loop_task = mock_task
    assert agent_runtime.is_running

    mock_task.done.return_value = True
    assert not agent_runtime.is_running

    agent_runtime._is_running_flag = False
    assert not agent_runtime.is_running

    agent_runtime._main_loop_task = None 
    assert not agent_runtime.is_running


@pytest.mark.asyncio
async def test_execution_loop_starts_and_processes_one_event(agent_runtime: AgentRuntime, mock_agent_context):
    test_event = UserMessageReceivedEvent(agent_input_user_message=AgentInputUserMessage(content="loop test"))
    assert isinstance(test_event, AgentOperationalEvent) # Verify it's operational

    # Simulate initial state for processing an operational event
    agent_runtime.context.status = AgentStatus.IDLE 
    
    # Mock get_next_input_event to return our test event then stop
    mock_agent_context.queues.get_next_input_event.side_effect = [
        ("user_message_input_queue", test_event), 
        asyncio.TimeoutError, # To allow loop to iterate once after processing event
        asyncio.TimeoutError, # To allow graceful stop
        None # To exit loop if stop is not fast enough
    ]
    
    mock_user_message_handler = AsyncMock()
    agent_runtime.event_handler_registry.get_handler = MagicMock(
        side_effect=lambda event_class: mock_user_message_handler if event_class == UserMessageReceivedEvent else None
    )

    with patch.object(agent_runtime.context.queues, 'enqueue_internal_system_event', new_callable=AsyncMock) as mock_enqueue_init, \
         patch.object(agent_runtime.status_manager, 'notify_processing_event_dequeued') as mock_notify_dequeued, \
         patch.object(agent_runtime.status_manager, 'notify_processing_complete_queues_empty') as mock_notify_empty:

        agent_runtime.start_execution_loop()
        await asyncio.sleep(0.05) # Allow loop to start, enqueue init, process one event, and timeout once

        # 1. Assert CreateToolInstancesEvent was enqueued at start
        found_create_tools_event = False
        for call in mock_enqueue_init.call_args_list:
            if isinstance(call.args[0], CreateToolInstancesEvent):
                found_create_tools_event = True
                break
        assert found_create_tools_event, "CreateToolInstancesEvent was not enqueued by _execution_loop start."
        
        # 2. Assert the UserMessageReceivedEvent was handled
        mock_user_message_handler.assert_called_once_with(test_event, mock_agent_context)
        
        # 3. Assert status manager interactions for operational event
        # Since status was IDLE and an AgentOperationalEvent came, it should transition to RUNNING
        mock_notify_dequeued.assert_called_once() 
        
        # After processing, if queues are empty (mocked to be), it should transition back to IDLE
        mock_notify_empty.assert_called_once()

        await agent_runtime.stop_execution_loop(timeout=0.1)

@pytest.mark.asyncio
async def test_execution_loop_timeout_from_get_next_event(agent_runtime: AgentRuntime, mock_agent_context):
    mock_agent_context.queues.get_next_input_event = AsyncMock(side_effect=asyncio.TimeoutError)
    
    # Set status to RUNNING to test the transition to IDLE on timeout + empty queues
    agent_runtime.context.status = AgentStatus.RUNNING 
    
    # Ensure queue.empty() returns True for the condition check
    mock_agent_context.queues._input_queues[0][1].empty.return_value = True


    with patch.object(agent_runtime.status_manager, 'notify_processing_complete_queues_empty') as mock_notify_idle:
        agent_runtime.start_execution_loop()
        await asyncio.sleep(0.01) # Allow loop to run and hit timeout
        
        mock_notify_idle.assert_called() # Should be called because status was RUNNING and timeout occurred with empty queues
        
        await agent_runtime.stop_execution_loop(timeout=0.1)

@pytest.mark.asyncio
async def test_execution_loop_terminates_on_stop_request(agent_runtime: AgentRuntime, mock_agent_context):
    # Make get_next_input_event block indefinitely until stop is requested
    stop_event_for_test = asyncio.Event()
    async def get_next_event_side_effect(*args, **kwargs):
        await stop_event_for_test.wait()
        return None # Return None after stop_event is set to allow loop to exit
    mock_agent_context.queues.get_next_input_event.side_effect = get_next_event_side_effect

    agent_runtime.start_execution_loop()
    await asyncio.sleep(0.001) # Ensure loop is running and blocked on get_next_input_event
    assert agent_runtime.is_running
        
    # Request stop, which should also set the stop_event_for_test to unblock get_next_input_event
    # The stop_execution_loop itself will set _stop_requested and enqueue AgentStoppedEvent.
    # The loop checks _stop_requested.
    stop_task = asyncio.create_task(agent_runtime.stop_execution_loop(timeout=0.2))
    await asyncio.sleep(0.01) # Give stop_execution_loop a moment to set _stop_requested
    stop_event_for_test.set() # Manually unblock the mocked get_next_input_event

    await asyncio.wait_for(stop_task, timeout=0.3) 

    assert not agent_runtime.is_running
    assert agent_runtime._main_loop_task is None 

@pytest.mark.asyncio
async def test_execution_loop_cancelled_externally(agent_runtime: AgentRuntime, mock_agent_context):
    block_event = asyncio.Event()
    async def blocking_get_event(*args, **kwargs):
        try:
            await block_event.wait()
        except asyncio.CancelledError: # Simulate get_next_input_event itself being cancelled
            raise
        return None 
    mock_agent_context.queues.get_next_input_event = AsyncMock(side_effect=blocking_get_event)

    agent_runtime.start_execution_loop()
    await asyncio.sleep(0.001) # Ensure loop task is created and running
    
    assert agent_runtime._main_loop_task is not None
    agent_runtime._main_loop_task.cancel() # External cancellation of the main loop task

    # Allow cancellation to propagate and be handled
    try:
        await asyncio.wait_for(agent_runtime._main_loop_task, timeout=0.1)
    except asyncio.CancelledError:
        pass # Expected
    
    assert not agent_runtime._is_running_flag # Flag should be false after loop exits
    # _main_loop_task might still exist but be .done()

@pytest.mark.asyncio
async def test_execution_loop_generic_exception(agent_runtime: AgentRuntime, mock_agent_context):
    test_exception = ValueError("Loop error")
    mock_agent_context.queues.get_next_input_event = AsyncMock(side_effect=test_exception)

    with patch.object(agent_runtime.status_manager, 'notify_error_occurred') as mock_notify_err_status, \
         patch.object(mock_agent_context.queues, 'enqueue_internal_system_event', new_callable=AsyncMock) as mock_enqueue_agent_error:
        
        agent_runtime.start_execution_loop()
        main_loop_task = agent_runtime._main_loop_task
        assert main_loop_task is not None
        
        # Wait for the loop task to complete (it should due to the exception)
        try:
            await asyncio.wait_for(main_loop_task, timeout=0.1)
        except ValueError as e: # Catch the specific error if it propagates (it shouldn't from the loop itself)
            if e is not test_exception: raise

        mock_notify_err_status.assert_called_once()
        # Check if AgentErrorEvent was enqueued
        enqueued_error_event = False
        for call in mock_enqueue_agent_error.call_args_list:
            if isinstance(call.args[0], AgentErrorEvent) and "Loop error" in call.args[0].error_message:
                enqueued_error_event = True
                break
        assert enqueued_error_event, "AgentErrorEvent with correct message was not enqueued."
            
        assert not agent_runtime._is_running_flag
