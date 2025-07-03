import pytest
import asyncio
import re
import xml.sax.saxutils
from unittest.mock import patch, MagicMock, Mock, call
from autobyteus.tools.timer import Timer
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from autobyteus.events.event_types import EventType

@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def sync_timer_instance():
    """A synchronous fixture that provides a clean Timer instance for each test."""
    return Timer()

# The async generator fixture 'timer_instance' is removed as it's causing issues.

def test_timer_default_init_config(sync_timer_instance: Timer):
    assert sync_timer_instance.duration == 300
    assert sync_timer_instance.interval == 60
    assert not sync_timer_instance._is_running

def test_timer_with_custom_instantiation_config():
    config = ToolConfig(params={'duration': 120, 'interval': 30})
    timer = Timer(config=config)
    assert timer.duration == 120
    assert timer.interval == 30

def test_tool_state_initialization():
    """Tests that the tool_state attribute is properly initialized."""
    tool = Timer()
    assert hasattr(tool, 'tool_state')
    assert isinstance(tool.tool_state, dict)
    assert tool.tool_state == {}
    # Verify it's usable
    tool.tool_state['last_start_time'] = 'now'
    assert tool.tool_state['last_start_time'] == 'now'

def test_get_name():
    assert Timer.get_name() == "Timer"

def test_get_description():
    desc = Timer.get_description()
    assert "Sets and runs a timer" in desc
    assert "Emits TIMER_UPDATE events" in desc

def test_get_config_schema_for_instantiation():
    schema = Timer.get_config_schema()
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2
    
    duration_param = schema.get_parameter('duration')
    assert isinstance(duration_param, ParameterDefinition)
    assert duration_param.param_type == ParameterType.INTEGER
    assert duration_param.default_value == 300
    
    interval_param = schema.get_parameter('interval')
    assert isinstance(interval_param, ParameterDefinition)
    assert interval_param.param_type == ParameterType.INTEGER
    assert interval_param.default_value == 60

def test_get_argument_schema_for_execution():
    schema = Timer.get_argument_schema()
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2
    
    duration_param = schema.get_parameter('duration')
    assert duration_param.name == "duration"
    assert duration_param.required is True
    
    interval_param = schema.get_parameter('interval')
    assert interval_param.name == "interval"
    assert interval_param.required is False

@pytest.mark.asyncio
async def test_execute_missing_duration_arg(sync_timer_instance: Timer, mock_agent_context):
    with pytest.raises(ValueError, match="Invalid arguments for tool 'Timer'"):
        await sync_timer_instance.execute(mock_agent_context)

@pytest.mark.asyncio
async def test_execute_starts_timer_with_given_duration_and_interval(sync_timer_instance: Timer, mock_agent_context):
    try:
        result = await sync_timer_instance.execute(mock_agent_context, duration=10, interval=5)
        
        assert "Timer started for 10 seconds, emitting events every 5 seconds." == result
        assert sync_timer_instance._is_running
        # The execute method does not change the instance's default duration/interval
        assert sync_timer_instance.duration == 300
        assert sync_timer_instance.interval == 60
    finally:
        await sync_timer_instance.stop()

@pytest.mark.asyncio
async def test_execute_uses_instance_interval_if_not_provided(sync_timer_instance: Timer, mock_agent_context):
    try:
        sync_timer_instance.set_interval(15)
        result = await sync_timer_instance.execute(mock_agent_context, duration=5)
        
        assert f"Timer started for 5 seconds, emitting events every 15 seconds." == result
        assert sync_timer_instance._is_running
        assert sync_timer_instance.interval == 15
    finally:
        await sync_timer_instance.stop()

def test_set_duration_valid(sync_timer_instance: Timer):
    sync_timer_instance.set_duration(100)
    assert sync_timer_instance.duration == 100

def test_set_duration_invalid(sync_timer_instance: Timer):
    with pytest.raises(ValueError):
        sync_timer_instance.set_duration(0)
    with pytest.raises(ValueError):
        sync_timer_instance.set_duration(86401)

def test_set_interval_valid(sync_timer_instance: Timer):
    sync_timer_instance.set_interval(30)
    assert sync_timer_instance.interval == 30

def test_set_interval_invalid(sync_timer_instance: Timer):
    with pytest.raises(ValueError):
        sync_timer_instance.set_interval(0)
    with pytest.raises(ValueError):
        sync_timer_instance.set_interval(3601)

@pytest.mark.asyncio
async def test_start_timer_already_running(sync_timer_instance: Timer):
    try:
        sync_timer_instance.set_duration(10)
        sync_timer_instance.start()
        assert sync_timer_instance._is_running
        # This call should be ignored and not raise an error
        sync_timer_instance.start()
    finally:
        await sync_timer_instance.stop()

@pytest.mark.asyncio
async def test_start_timer_no_duration_set(sync_timer_instance: Timer):
    # This test does not start a task, so no cleanup needed.
    sync_timer_instance.duration = 0
    with pytest.raises(RuntimeError, match="Timer duration must be positive and set before starting"):
        sync_timer_instance.start()

@pytest.mark.asyncio
async def test_timer_event_emission_flow(sync_timer_instance: Timer):
    # This test waits for the task to complete, so the finally block is a safety net.
    try:
        events_emitted = []
        def event_handler(event_type, **kwargs):
            events_emitted.append((event_type, kwargs))
        
        sync_timer_instance.subscribe(EventType.TIMER_UPDATE, event_handler)
        
        test_duration = 2
        test_interval = 1
        sync_timer_instance.start(run_duration=test_duration, run_interval=test_interval)
        
        await asyncio.sleep(test_duration + 0.5)
        
        assert len(events_emitted) >= 2
        
        remaining_times_recorded = [e[1]['remaining_time'] for e in events_emitted if e[0] == EventType.TIMER_UPDATE]
        assert test_duration in remaining_times_recorded
        assert 0 in remaining_times_recorded 
        if test_duration >= test_interval:
             assert test_duration - test_interval in remaining_times_recorded

        assert not sync_timer_instance._is_running
    finally:
        await sync_timer_instance.stop()

@pytest.mark.asyncio
async def test_stop_timer(sync_timer_instance: Timer, mock_agent_context):
    try:
        await sync_timer_instance.execute(mock_agent_context, duration=10, interval=1)
        assert sync_timer_instance._is_running
        
        await sync_timer_instance.stop()
        assert not sync_timer_instance._is_running
        assert sync_timer_instance._task is None or sync_timer_instance._task.done()
    finally:
        # Extra stop in finally is safe and ensures cleanup if asserts fail
        await sync_timer_instance.stop()

@pytest.mark.asyncio
async def test_execute_cancels_previous_timer(sync_timer_instance: Timer, mock_agent_context):
    try:
        await sync_timer_instance.execute(mock_agent_context, duration=10, interval=1)
        first_task = sync_timer_instance._task
        assert first_task is not None and not first_task.done()

        await sync_timer_instance.execute(mock_agent_context, duration=5, interval=1)
        second_task = sync_timer_instance._task
        
        assert first_task.cancelled() or first_task.done()
        assert second_task is not None and not second_task.done()
        assert second_task is not first_task
    finally:
        await sync_timer_instance.stop()
