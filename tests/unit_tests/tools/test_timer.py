import pytest
import asyncio
import re
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
    """A synchronous fixture for tests that don't start the timer task."""
    return Timer()

@pytest.fixture
async def timer_instance():
    """An async fixture that provides a timer and ensures it's cleaned up."""
    timer = Timer()
    yield timer
    if timer._task and not timer._task.done():
        await timer.stop()

def test_timer_default_init_config(sync_timer_instance: Timer):
    assert sync_timer_instance.duration == 300
    assert sync_timer_instance.interval == 60
    assert not sync_timer_instance._is_running

def test_timer_with_custom_instantiation_config():
    config = ToolConfig(params={'duration': 120, 'interval': 30})
    timer = Timer(config=config)
    assert timer.duration == 120
    assert timer.interval == 30

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

def test_tool_usage_xml_output():
    xml_output = Timer.tool_usage_xml()
    
    assert '<command name="Timer">' in xml_output
    assert '</command>' in xml_output

    duration_match = re.search(r'<arg name="duration".*?/>', xml_output)
    assert duration_match is not None
    duration_tag = duration_match.group(0)
    assert 'type="integer"' in duration_tag
    assert 'required="true"' in duration_tag
    assert 'description="Duration to set for this timer run in seconds."' in duration_tag

    interval_match = re.search(r'<arg name="interval".*?/>', xml_output)
    assert interval_match is not None
    interval_tag = interval_match.group(0)
    assert 'type="integer"' in interval_tag
    assert 'required="false"' in interval_tag
    assert 'description="Interval for emitting timer events in seconds for this run. Overrides instance default."' in interval_tag


def test_tool_usage_json_output():
    json_output = Timer.tool_usage_json()
    assert json_output["name"] == "Timer"
    input_schema = json_output["inputSchema"]
    assert "duration" in input_schema["properties"]
    assert "interval" in input_schema["properties"]
    assert "duration" in input_schema["required"]
    assert "interval" not in input_schema["required"]


@pytest.mark.asyncio
async def test_execute_missing_duration_arg(timer_instance: Timer, mock_agent_context):
    with pytest.raises(ValueError, match="Invalid arguments for tool 'Timer'"):
        await timer_instance.execute(mock_agent_context)

@pytest.mark.asyncio
async def test_execute_starts_timer_with_given_duration_and_interval(timer_instance: Timer, mock_agent_context):
    result = await timer_instance.execute(mock_agent_context, duration=10, interval=5)
    
    assert "Timer started for 10 seconds, emitting events every 5 seconds." == result
    assert timer_instance._is_running
    assert timer_instance.duration == 300
    assert timer_instance.interval == 60

@pytest.mark.asyncio
async def test_execute_uses_instance_interval_if_not_provided(timer_instance: Timer, mock_agent_context):
    timer_instance.set_interval(15)
    result = await timer_instance.execute(mock_agent_context, duration=5)
    
    assert f"Timer started for 5 seconds, emitting events every 15 seconds." == result
    assert timer_instance._is_running
    assert timer_instance.interval == 15

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
async def test_start_timer_already_running(timer_instance: Timer):
    timer_instance.set_duration(10)
    timer_instance.start()
    assert timer_instance._is_running
    timer_instance.start()

@pytest.mark.asyncio
async def test_start_timer_no_duration_set(timer_instance: Timer):
    timer_instance.duration = 0
    with pytest.raises(RuntimeError, match="Timer duration must be positive and set before starting"):
        timer_instance.start()

@pytest.mark.asyncio
async def test_timer_event_emission_flow(timer_instance: Timer):
    events_emitted = []
    def event_handler(event_type, **kwargs):
        events_emitted.append((event_type, kwargs))
    
    timer_instance.subscribe(EventType.TIMER_UPDATE, event_handler)
    
    test_duration = 2
    test_interval = 1
    timer_instance.start(run_duration=test_duration, run_interval=test_interval)
    
    await asyncio.sleep(test_duration + 0.5)
    
    assert len(events_emitted) >= 2
    
    remaining_times_recorded = [e[1]['remaining_time'] for e in events_emitted if e[0] == EventType.TIMER_UPDATE]
    assert test_duration in remaining_times_recorded
    assert 0 in remaining_times_recorded 
    if test_duration >= test_interval:
         assert test_duration - test_interval in remaining_times_recorded

    assert not timer_instance._is_running

@pytest.mark.asyncio
async def test_stop_timer(timer_instance: Timer, mock_agent_context):
    await timer_instance.execute(mock_agent_context, duration=10, interval=1)
    assert timer_instance._is_running
    
    await timer_instance.stop()
    assert not timer_instance._is_running
    assert timer_instance._task is None or timer_instance._task.done()

@pytest.mark.asyncio
async def test_execute_cancels_previous_timer(timer_instance: Timer, mock_agent_context):
    await timer_instance.execute(mock_agent_context, duration=10, interval=1)
    first_task = timer_instance._task
    assert first_task is not None and not first_task.done()

    await timer_instance.execute(mock_agent_context, duration=5, interval=1)
    second_task = timer_instance._task
    
    assert first_task.cancelled() or first_task.done()
    assert second_task is not None and not second_task.done()
    assert second_task is not first_task
