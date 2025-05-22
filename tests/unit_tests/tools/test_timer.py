import pytest
import asyncio
from unittest.mock import patch, MagicMock, Mock # Added Mock
from autobyteus.tools.timer import Timer
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ParameterType
from autobyteus.events.event_types import EventType

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.mark.asyncio
async def test_timer_default_config():
    timer = Timer()
    assert timer.duration == 300
    assert timer.interval == 60
    assert not timer._is_running

@pytest.mark.asyncio
async def test_timer_with_custom_config():
    config = ToolConfig(params={'duration': 120, 'interval': 30})
    timer = Timer(config=config)
    assert timer.duration == 120
    assert timer.interval == 30

@pytest.mark.asyncio
async def test_get_config_schema(): # Removed mock_agent_context
    schema = Timer.get_config_schema()
    assert len(schema) == 2
    
    duration_param = schema.get_parameter('duration')
    assert duration_param is not None
    assert duration_param.param_type == ParameterType.INTEGER
    assert duration_param.default_value == 300
    assert duration_param.min_value == 1
    assert duration_param.max_value == 86400
    
    interval_param = schema.get_parameter('interval')
    assert interval_param is not None
    assert interval_param.param_type == ParameterType.INTEGER
    assert interval_param.default_value == 60

@pytest.mark.asyncio
async def test_tool_usage_xml(): # Removed mock_agent_context
    usage = Timer.tool_usage_xml()
    
    assert 'Timer: Sets and runs a timer, emitting events with remaining time.' in usage
    assert '<command name="Timer">' in usage
    assert '<arg name="duration">300</arg>' in usage
    assert '<arg name="interval" optional="true">60</arg>' in usage

@pytest.mark.asyncio
async def test_execute_missing_duration(mock_agent_context): # Added mock_agent_context
    timer = Timer()
    
    with pytest.raises(ValueError, match="Timer duration must be provided"):
        await timer.execute(mock_agent_context) # Added mock_agent_context

@pytest.mark.asyncio
async def test_execute_with_duration(mock_agent_context): # Added mock_agent_context
    timer = Timer()
    
    result = await timer.execute(mock_agent_context, duration=10, interval=5) # Added mock_agent_context
    
    assert "Timer started for 10 seconds, emitting events every 5 seconds" == result
    assert timer.duration == 10
    assert timer.interval == 5
    assert timer._is_running
    # Clean up the task
    if timer._task:
        timer._task.cancel()
        try:
            await timer._task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_set_duration():
    timer = Timer()
    timer.set_duration(100)
    assert timer.duration == 100

@pytest.mark.asyncio
async def test_set_interval():
    timer = Timer()
    timer.set_interval(30)
    assert timer.interval == 30

@pytest.mark.asyncio
async def test_start_timer_already_running():
    timer = Timer()
    timer.set_duration(10)
    timer.start()
    
    with pytest.raises(RuntimeError, match="Timer is already running"):
        timer.start()
    
    # Clean up
    if timer._task:
        timer._task.cancel()
        try:
            await timer._task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_start_timer_no_duration():
    timer = Timer()
    timer.set_duration(0) # Duration must be > 0
    
    with pytest.raises(RuntimeError, match="Timer duration must be set before starting"): # Source has "Timer duration must be set before starting"
        timer.start()

def test_get_name():
    assert Timer.get_name() == "Timer"

@pytest.mark.asyncio
async def test_timer_event_emission():
    timer = Timer()
    events_emitted = []

    def event_handler(event_type, **kwargs):
        events_emitted.append((event_type, kwargs))
    
    timer.subscribe(EventType.TIMER_UPDATE, event_handler)
    
    # Set a very short timer for testing
    timer.set_duration(1)
    timer.set_interval(1) # Ensure interval allows emission before completion
    timer.start()
    
    # Wait for timer to complete + a buffer
    await asyncio.sleep(1.5) # Adjusted sleep time for reliability
    
    # Check that events were emitted
    assert len(events_emitted) >= 1, "No events emitted"
    # The first event might be at duration, last at 0
    first_event_ok = any(event[0] == EventType.TIMER_UPDATE and event[1]['remaining_time'] == 1 for event in events_emitted)
    last_event_ok = any(event[0] == EventType.TIMER_UPDATE and event[1]['remaining_time'] == 0 for event in events_emitted)
    assert first_event_ok, "Timer start event with initial remaining time not found"
    assert last_event_ok, "Timer end event with 0 remaining time not found"
    
    # Clean up
    if timer._task and not timer._task.done():
        timer._task.cancel()
        try:
            await timer._task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_execute_with_default_interval(mock_agent_context): # Added mock_agent_context
    timer = Timer()
    
    result = await timer.execute(mock_agent_context, duration=5) # Added mock_agent_context
    
    assert "Timer started for 5 seconds, emitting events every 60 seconds" == result
    assert timer.duration == 5
    assert timer.interval == 60 # Default interval
    
    # Clean up
    if timer._task:
        timer._task.cancel()
        try:
            await timer._task
        except asyncio.CancelledError:
            pass
