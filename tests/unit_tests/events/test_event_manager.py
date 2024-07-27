# File: autobyteus/tests/unit_tests/events/test_event_manager.py

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
        assert dummy_listener in manager.listeners[EventType.TOOL_EXECUTION_STARTED]

    def test_unsubscribe(self):
        manager = EventManager()
        def dummy_listener(): pass
        manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        manager.unsubscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        assert dummy_listener not in manager.listeners[EventType.TOOL_EXECUTION_STARTED]

    def test_emit(self):
        manager = EventManager()
        result = []
        def dummy_listener(value):
            result.append(value)
        manager.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        manager.emit(EventType.TOOL_EXECUTION_STARTED, "test")
        assert result == ["test"]