
import pytest
from autobyteus.events.event_manager import EventManager
from autobyteus.events.event_types import EventType

@pytest.fixture
def manager():
    return EventManager()

def test_init(manager):
    assert isinstance(manager.listeners, dict)

def test_subscribe(manager):
    def dummy_listener(**kwargs):
        pass
    manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
    assert dummy_listener in manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]

def test_unsubscribe(manager):
    def dummy_listener(**kwargs):
        pass
    manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
    manager.unsubscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
    assert (
        EventType.TOOL_EXECUTION_STARTED not in manager.listeners
        or None not in manager.listeners[EventType.TOOL_EXECUTION_STARTED]
        or dummy_listener not in manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]
    )

def test_emit(manager):
    result = []

    def dummy_listener(value, **kwargs):
        result.append(value)

    manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
    manager.emit(EventType.TOOL_EXECUTION_STARTED, None, "test")
    assert result == ["test"]

def test_emit_with_object_id(manager):
    result = []

    def dummy_listener(*args, **kwargs):
        result.append((args, kwargs))

    test_object_id = "test_object"
    manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener, object_id=test_object_id)
    manager.emit(EventType.TOOL_EXECUTION_STARTED, test_object_id, "test_value", extra_param="extra")

    assert len(result) == 1
    args, kwargs = result[0]
    assert args == ("test_value",)
    assert kwargs == {"object_id": test_object_id, "extra_param": "extra"}
