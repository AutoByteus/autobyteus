import pytest
from autobyteus.events.event_manager import EventManager
from autobyteus.events.event_types import EventType

class TestEventManager:
    def test_init(self):
        manager = EventManager()
        assert isinstance(manager.listeners, dict)

    def test_subscribe(self):
        manager = EventManager()
        def dummy_listener(): pass
        manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        assert dummy_listener in manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]

    def test_unsubscribe(self):
        manager = EventManager()
        def dummy_listener(): pass
        manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        manager.unsubscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        assert EventType.TOOL_EXECUTION_STARTED not in manager.listeners or \
               None not in manager.listeners[EventType.TOOL_EXECUTION_STARTED] or \
               dummy_listener not in manager.listeners[EventType.TOOL_EXECUTION_STARTED][None]

    def test_emit(self):
        manager = EventManager()
        result = []
        def dummy_listener(value):
            result.append(value)
        manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        manager.emit(EventType.TOOL_EXECUTION_STARTED, None, "test")
        assert result == ["test"]

    def test_emit_with_agent_id(self):
        manager = EventManager()
        result = []
        def dummy_listener(*args, **kwargs):
            result.append((args, kwargs))
        
        test_agent_id = "test_agent"
        manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener, test_agent_id)
        manager.emit(EventType.TOOL_EXECUTION_STARTED, test_agent_id, "test_value", extra_param="extra")
        
        assert len(result) == 1
        args, kwargs = result[0]
        assert args == ("test_value",)
        assert kwargs == {"agent_id": test_agent_id, "extra_param": "extra"}