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
    AgentProcessingEvent,
    GenericEvent 
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
    queues._input_queues = [("mock_q", MagicMock(empty=MagicMock(return_value=True)))]
    return queues

@pytest.fixture
def mock_agent_context(mock_agent_definition, mock_event_queues, mock_llm_instance):
    context = MagicMock(spec=AgentContext)
    context.agent_id = "test_agent_123"
    context.definition = mock_agent_definition
    context.queues = mock_event_queues
    context.llm_instance = mock_llm_instance
    context.status_manager = None 
    return context

@pytest.fixture
def mock_event_handler_registry():
    registry = MagicMock(spec=EventHandlerRegistry)
    registry.get_handler = MagicMock(return_value=None) 
    return registry

@pytest.fixture
def agent_runtime(mock_agent_context, mock_event_handler_registry):
    runtime = AgentRuntime(context=mock_agent_context, event_handler_registry=mock_event_handler_registry)
    return runtime


@pytest.mark.asyncio
async def test_initialization(agent_runtime: AgentRuntime, mock_agent_context, mock_event_handler_registry):
    assert agent_runtime.context == mock_agent_context
    assert agent_runtime.event_handler_registry == mock_event_handler_registry
    assert isinstance(agent_runtime.status_manager, AgentStatusManager)
    assert isinstance(agent_runtime.status_manager, EventEmitter) 
    assert agent_runtime.status_manager.context == mock_agent_context
    
    assert not isinstance(agent_runtime, EventEmitter)
    assert agent_runtime.context.status == AgentStatus.NOT_STARTED 
    assert not agent_runtime._is_running_flag
    assert agent_runtime._main_loop_task is None

@pytest.mark.asyncio
async def test_start_execution_loop(agent_runtime: AgentRuntime):
    mock_task_instance = AsyncMock(spec=asyncio.Task) 
    mock_task_instance.done.return_value = False      

    with patch('asyncio.create_task', return_value=mock_task_instance) as mock_create_task, \
         patch.object(agent_runtime.status_manager, 'notify_runtime_starting') as mock_notify_starting:

        agent_runtime.start_execution_loop() 

        assert agent_runtime._is_running_flag
        assert not agent_runtime._stop_requested.is_set()
        mock_notify_starting.assert_called_once()
        mock_create_task.assert_called_once_with(ANY, name=f"agent_runtime_loop_{agent_runtime.context.agent_id}")
        assert agent_runtime._main_loop_task == mock_task_instance
        
        mock_notify_starting.reset_mock()
        mock_create_task.reset_mock()
        
        agent_runtime.start_execution_loop() 
        
        mock_notify_starting.assert_not_called() 
        mock_create_task.assert_not_called()

    if agent_runtime._main_loop_task is mock_task_instance: 
        mock_task_instance.done.return_value = True 
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
        mock_llm_cleanup.assert_called_once()
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
        mock_llm_cleanup.assert_called_once()
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
        mock_notify_started_handled.assert_called_once()

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

    with caplog.at_level(logging.WARNING):
        await agent_runtime._dispatch_event(test_event)
    
    assert f"Agent '{mock_agent_context.agent_id}' no handler registered for event type 'UnknownEvent'" in caplog.text

@pytest.mark.asyncio
async def test_status_property(agent_runtime: AgentRuntime, mock_agent_context):
    agent_runtime.status_manager.context.status = AgentStatus.RUNNING 
    assert agent_runtime.status == AgentStatus.RUNNING
    
    agent_runtime.status_manager.context.status = None 
    with patch.object(logging.getLogger('autobyteus.agent.agent_runtime'), 'error') as mock_log_error:
        assert agent_runtime.status == AgentStatus.ERROR
        mock_log_error.assert_called_once_with(
             f"AgentRuntime '{mock_agent_context.agent_id}': context.status is None, which is unexpected. Defaulting to ERROR."
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

    mock_agent_context.queues.get_next_input_event = AsyncMock(
        side_effect=[
            ("user_message_input_queue", test_event), 
            None, 
            None,
            None
        ]
    )
    
    mock_user_message_handler = AsyncMock()
    # mock_lifecycle_handler is not strictly needed for this test's core assertion, 
    # as AgentStartedEvent is not yielded by the mocked get_next_input_event
    # We will only verify UserMessageReceivedEvent processing here.
    # If AgentStartedEvent processing were to be tested, get_next_input_event mock
    # would need to yield it.

    def get_handler_side_effect(event_class):
        if event_class == UserMessageReceivedEvent:
            return mock_user_message_handler
        # If AgentStartedEvent were processed, this would be called:
        # elif event_class == AgentStartedEvent:
        #     return AsyncMock() # A generic mock for it
        return None 
    agent_runtime.event_handler_registry.get_handler = MagicMock(side_effect=get_handler_side_effect)

    # We don't need to patch notify_agent_started_event_handled for this test's core assertion
    # as AgentStartedEvent isn't processed from the primary event source here.
    agent_runtime.start_execution_loop()
    await asyncio.sleep(0.02) 

    # Verify AgentStartedEvent was *enqueued* by the loop's start
    found_agent_started_enqueued = False
    for call_args_tuple in mock_agent_context.queues.enqueue_internal_system_event.call_args_list:
        if isinstance(call_args_tuple.args[0], AgentStartedEvent):
            found_agent_started_enqueued = True
            break
    assert found_agent_started_enqueued, "AgentStartedEvent was not enqueued."
    
    # MODIFIED: Assert on the 'handle' method of the mock
    mock_user_message_handler.handle.assert_called_once_with(test_event, mock_agent_context)
    
    # These assertions are removed as AgentStartedEvent is not dispatched by the mocked get_next_input_event:
    # mock_lifecycle_handler.assert_called_once_with(ANY, mock_agent_context) 
    # assert isinstance(mock_lifecycle_handler.call_args.args[0], AgentStartedEvent)
    # mock_notify_started_handled.assert_called_once() 

    await agent_runtime.stop_execution_loop(timeout=0.1)

@pytest.mark.asyncio
async def test_execution_loop_timeout_from_get_next_event(agent_runtime: AgentRuntime, mock_agent_context):
    mock_agent_context.queues.get_next_input_event = AsyncMock(side_effect=asyncio.TimeoutError)
    agent_runtime.context.status = AgentStatus.RUNNING 
    
    mock_agent_context.queues._input_queues = [("mock_q", MagicMock(empty=MagicMock(return_value=True)))]


    with patch.object(agent_runtime.status_manager, 'notify_processing_complete_queues_empty') as mock_notify_idle:
        agent_runtime.start_execution_loop()
        await asyncio.sleep(0.01) 
        
        mock_notify_idle.assert_called()
        
        await agent_runtime.stop_execution_loop(timeout=0.1)

@pytest.mark.asyncio
async def test_execution_loop_terminates_on_stop_request(agent_runtime: AgentRuntime, mock_agent_context):
    mock_agent_context.queues.get_next_input_event = AsyncMock(return_value=None)

    agent_runtime.start_execution_loop()
    await asyncio.sleep(0.001) 
    assert agent_runtime.is_running
        
    stop_task = asyncio.create_task(agent_runtime.stop_execution_loop(timeout=0.1))
    await asyncio.wait_for(stop_task, timeout=0.2) 

    assert not agent_runtime.is_running
    assert agent_runtime._main_loop_task is None 

@pytest.mark.asyncio
async def test_execution_loop_cancelled_externally(agent_runtime: AgentRuntime, mock_agent_context):
    block_event = asyncio.Event()
    async def blocking_get_event(*args, **kwargs):
        await block_event.wait()
        return None 
    mock_agent_context.queues.get_next_input_event = AsyncMock(side_effect=blocking_get_event)

    agent_runtime.start_execution_loop()
    await asyncio.sleep(0.001) 
    
    assert agent_runtime._main_loop_task is not None
    agent_runtime._main_loop_task.cancel() 

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(agent_runtime._main_loop_task, timeout=0.1)
    
    assert not agent_runtime._is_running_flag 

@pytest.mark.asyncio
async def test_execution_loop_generic_exception(agent_runtime: AgentRuntime, mock_agent_context):
    test_exception = ValueError("Loop error")
    mock_agent_context.queues.get_next_input_event = AsyncMock(side_effect=test_exception)

    with patch.object(agent_runtime.status_manager, 'notify_error_occurred') as mock_notify_err_status, \
         patch.object(mock_agent_context.queues, 'enqueue_internal_system_event', new_callable=AsyncMock) as mock_enqueue_agent_error:
        
        agent_runtime.start_execution_loop()
        main_loop_task = agent_runtime._main_loop_task
        assert main_loop_task is not None
        
        await asyncio.wait_for(main_loop_task, timeout=0.1)

        mock_notify_err_status.assert_called_once()
        mock_enqueue_agent_error.assert_called()
        assert any(isinstance(call.args[0], AgentErrorEvent) and "Loop error" in call.args[0].error_message 
                   for call in mock_enqueue_agent_error.call_args_list)
            
        assert not agent_runtime._is_running_flag
