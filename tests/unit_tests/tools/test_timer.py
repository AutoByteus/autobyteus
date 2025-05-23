import pytest
import asyncio
from unittest.mock import patch, MagicMock, Mock, call
from autobyteus.tools.timer import Timer
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Updated
from autobyteus.events.event_types import EventType

@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
async def timer_instance(): # Fixture to provide a fresh timer instance and ensure cleanup
    timer = Timer()
    yield timer
    # Cleanup: stop the timer if it's running to prevent tasks bleeding into other tests
    if timer._task and not timer._task.done():
        await timer.stop()

def test_timer_default_init_config(timer_instance: Timer): # Use fixture
    assert timer_instance.duration == 300
    assert timer_instance.interval == 60
    assert not timer_instance._is_running

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
    schema = Timer.get_config_schema() # For instantiation
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
    schema = Timer.get_argument_schema() # For execution
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2 # duration, interval
    
    duration_param = schema.get_parameter('duration')
    assert duration_param.name == "duration"
    assert duration_param.required is True
    
    interval_param = schema.get_parameter('interval')
    assert interval_param.name == "interval"
    assert interval_param.required is False # Optional override for execution

def test_tool_usage_xml_output():
    xml_output = Timer.tool_usage_xml()
    assert '<command name="Timer">' in xml_output
    assert '<arg name="duration" type="integer" required="true"' in xml_output
    assert '<arg name="interval" type="integer" required="false"' in xml_output # interval is optional for execute

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
        await timer_instance.execute(mock_agent_context) # Missing 'duration'

@pytest.mark.asyncio
async def test_execute_starts_timer_with_given_duration_and_interval(timer_instance: Timer, mock_agent_context):
    result = await timer_instance.execute(mock_agent_context, duration=10, interval=5)
    
    assert "Timer started for 10 seconds, emitting events every 5 seconds" == result
    assert timer_instance._is_running
    # The timer's instance duration/interval are not changed by execute, it uses them for the run
    assert timer_instance.duration == 300 # Instance default not changed
    assert timer_instance.interval == 60  # Instance default not changed

@pytest.mark.asyncio
async def test_execute_uses_instance_interval_if_not_provided(timer_instance: Timer, mock_agent_context):
    timer_instance.set_interval(15) # Set instance interval
    result = await timer_instance.execute(mock_agent_context, duration=5) # No interval in execute
    
    assert f"Timer started for 5 seconds, emitting events every 15 seconds" == result
    assert timer_instance._is_running
    assert timer_instance.interval == 15

# Test set_duration and set_interval (programmatic direct use)
def test_set_duration_valid(timer_instance: Timer):
    timer_instance.set_duration(100)
    assert timer_instance.duration == 100

def test_set_duration_invalid(timer_instance: Timer):
    with pytest.raises(ValueError):
        timer_instance.set_duration(0)
    with pytest.raises(ValueError):
        timer_instance.set_duration(86401)

def test_set_interval_valid(timer_instance: Timer):
    timer_instance.set_interval(30)
    assert timer_instance.interval == 30

def test_set_interval_invalid(timer_instance: Timer):
    with pytest.raises(ValueError):
        timer_instance.set_interval(0)
    with pytest.raises(ValueError):
        timer_instance.set_interval(3601)

# Test direct start method
@pytest.mark.asyncio
async def test_start_timer_already_running(timer_instance: Timer):
    timer_instance.set_duration(10)
    timer_instance.start() # Starts the timer
    assert timer_instance._is_running
    # Calling start again should ideally log and return, not raise error
    timer_instance.start() # Should be idempotent or log, not raise
    # To check if RuntimeError is raised, then expect it. Based on code, it logs and returns.
    # Previous test for this:
    # with pytest.raises(RuntimeError, match="Timer is already running"):
    # The current `start` logs and returns if already running.

@pytest.mark.asyncio
async def test_start_timer_no_duration_set(timer_instance: Timer):
    timer_instance.duration = 0 # Invalid duration for start
    with pytest.raises(RuntimeError, match="Timer duration must be positive and set before starting"):
        timer_instance.start()

@pytest.mark.asyncio
async def test_timer_event_emission_flow(timer_instance: Timer):
    events_emitted = []
    def event_handler(event_type, **kwargs):
        events_emitted.append((event_type, kwargs))
    
    timer_instance.subscribe(EventType.TIMER_UPDATE, event_handler)
    
    # Use direct start for more control over duration/interval in this test
    test_duration = 2
    test_interval = 1
    timer_instance.start(run_duration=test_duration, run_interval=test_interval)
    
    await asyncio.sleep(test_duration + 0.5) # Wait for timer to complete + buffer
    
    assert len(events_emitted) >= 2 # At least start (2s), 1s, and 0s event
    
    # Check for specific remaining times
    remaining_times_recorded = [e[1]['remaining_time'] for e in events_emitted if e[0] == EventType.TIMER_UPDATE]
    assert test_duration in remaining_times_recorded
    assert 0 in remaining_times_recorded 
    if test_duration >= test_interval:
         assert test_duration - test_interval in remaining_times_recorded # e.g. 1s if duration=2, interval=1

    assert not timer_instance._is_running # Should be false after completion

@pytest.mark.asyncio
async def test_stop_timer(timer_instance: Timer, mock_agent_context):
    await timer_instance.execute(mock_agent_context, duration=10, interval=1) # Start it
    assert timer_instance._is_running
    
    await timer_instance.stop()
    assert not timer_instance._is_running
    assert timer_instance._task is None or timer_instance._task.done()

    # Verify if a cancellation event was emitted (optional, depends on desired behavior)
    # For this, the event handler would need to be set up.

@pytest.mark.asyncio
async def test_execute_cancels_previous_timer(timer_instance: Timer, mock_agent_context):
    # Start a first timer
    await timer_instance.execute(mock_agent_context, duration=10, interval=1)
    first_task = timer_instance._task
    assert first_task is not None and not first_task.done()

    # Execute again, which should cancel the first and start a new one
    await timer_instance.execute(mock_agent_context, duration=5, interval=1)
    second_task = timer_instance._task
    
    assert first_task.cancelled() or first_task.done() # Should be cancelled or finished quickly
    assert second_task is not None and not second_task.done()
    assert second_task is not first_task

