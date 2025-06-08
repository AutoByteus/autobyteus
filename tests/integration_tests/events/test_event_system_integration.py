# File: autobyteus/tests/integration_tests/events/test_event_system_integration.py

import pytest
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType
from autobyteus.events.decorators import publish_event, event_listener

class TestTool(EventEmitter):
    def __init__(self):
        super().__init__()
        self.execution_completed = False

    @publish_event(EventType.TOOL_EXECUTION_COMPLETED)
    def execute(self):
        return "Execution result"

    @event_listener(EventType.TOOL_EXECUTION_COMPLETED)
    def on_execution_completed(self, result, **kwargs):
        self.execution_completed = True
        self.execution_result = result

def test_full_event_flow():
    tool = TestTool()
    result = tool.execute()
    
    assert result == "Execution result"
    assert tool.execution_completed
    assert tool.execution_result == "Execution result"

def test_multiple_listeners():
    tool = TestTool()
    external_result = []
    
    @event_listener(EventType.TOOL_EXECUTION_COMPLETED)
    def external_listener(result, **kwargs):
        external_result.append(result)
    
    tool.subscribe(EventType.TOOL_EXECUTION_COMPLETED, external_listener)
    
    tool.execute()
    
    assert tool.execution_completed
    assert tool.execution_result == "Execution result"
    assert external_result == ["Execution result"]

def test_unsubscribe():
    tool = TestTool()
    external_result = []
    
    @event_listener(EventType.TOOL_EXECUTION_COMPLETED)
    def external_listener(result, **kwargs):
        external_result.append(result)
    
    tool.subscribe(EventType.TOOL_EXECUTION_COMPLETED, external_listener)
    tool.unsubscribe(EventType.TOOL_EXECUTION_COMPLETED, external_listener)
    
    tool.execute()
    
    assert tool.execution_completed
    assert tool.execution_result == "Execution result"
    assert len(external_result) == 0
