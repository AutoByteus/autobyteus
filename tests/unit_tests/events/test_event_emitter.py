# File: autobyteus/tests/unit_tests/events/test_event_emitter.py

import pytest
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

class TestEventEmitter:
    def test_init(self):
        emitter = EventEmitter()
        assert hasattr(emitter, 'event_manager')

    def test_subscribe(self):
        emitter = EventEmitter()
        def dummy_listener(): pass
        emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        assert dummy_listener in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED]

    def test_unsubscribe(self):
        emitter = EventEmitter()
        def dummy_listener(): pass
        emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        emitter.unsubscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        assert dummy_listener not in emitter.event_manager.listeners[EventType.TOOL_EXECUTION_STARTED]

    def test_emit(self):
        emitter = EventEmitter()
        result = []
        def dummy_listener(value):
            result.append(value)
        emitter.subscribe(EventType.TOOL_EXECUTION_STARTED, dummy_listener)
        emitter.emit(EventType.TOOL_EXECUTION_STARTED, "test")
        assert result == ["test"]