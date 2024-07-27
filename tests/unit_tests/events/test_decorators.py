# File: autobyteus/tests/unit_tests/events/test_decorators.py

import pytest
from autobyteus.events.decorators import publish_event, event_listener
from autobyteus.events.event_types import EventType
from autobyteus.events.event_emitter import EventEmitter

class DummyEmitter(EventEmitter):
    @publish_event(EventType.TOOL_EXECUTION_COMPLETED)
    def dummy_method(self):
        return "Result"

    @event_listener(EventType.TOOL_EXECUTION_COMPLETED)
    def dummy_listener(self, result):
        self.listened_result = result

def test_publish_event_decorator():
    emitter = DummyEmitter()
    result = emitter.dummy_method()
    assert result == "Result"
    # The actual event emission is tested in integration tests

def test_event_listener_decorator():
    emitter = DummyEmitter()
    assert hasattr(emitter.dummy_listener, '_is_event_listener')
    assert emitter.dummy_listener._event_type == EventType.TOOL_EXECUTION_COMPLETED