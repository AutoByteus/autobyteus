
import pytest
from autobyteus.events.decorators import publish_event, event_listener
from autobyteus.events.event_types import EventType
from autobyteus.events.event_emitter import EventEmitter

class TestEmitter(EventEmitter):
    @publish_event(EventType.TOOL_EXECUTION_COMPLETED)
    def execute_tool(self):
        return "Tool Executed"

    @event_listener(EventType.TOOL_EXECUTION_COMPLETED)
    def on_tool_completed(self, result):
        self.result = result

def test_publish_event_decorator():
    emitter = TestEmitter()
    result = emitter.execute_tool()
    assert result == "Tool Executed"
    assert hasattr(emitter, 'result')
    assert emitter.result == "Tool Executed"

def test_event_listener_decorator():
    emitter = TestEmitter()
    assert hasattr(emitter.on_tool_completed, '_is_event_listener')
    assert emitter.on_tool_completed._event_type == EventType.TOOL_EXECUTION_COMPLETED
