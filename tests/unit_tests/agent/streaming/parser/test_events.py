"""
Unit tests for the streaming parser events module.
"""
import pytest
from autobyteus.agent.streaming.parser.events import (
    SegmentEvent,
    SegmentType,
    SegmentEventType,
)


class TestSegmentType:
    """Tests for SegmentType enum."""

    def test_segment_type_values(self):
        """Verify all expected segment types exist with correct values."""
        assert SegmentType.TEXT.value == "text"
        assert SegmentType.TOOL_CALL.value == "tool_call"
        assert SegmentType.FILE.value == "file"
        assert SegmentType.BASH.value == "bash"
        assert SegmentType.IFRAME.value == "iframe"
        assert SegmentType.THOUGHT.value == "thought"


class TestSegmentEventType:
    """Tests for SegmentEventType enum."""

    def test_event_type_values(self):
        """Verify all expected event types exist with correct values."""
        assert SegmentEventType.START.value == "SEGMENT_START"
        assert SegmentEventType.CONTENT.value == "SEGMENT_CONTENT"
        assert SegmentEventType.END.value == "SEGMENT_END"


class TestSegmentEvent:
    """Tests for SegmentEvent dataclass."""

    def test_start_factory(self):
        """Test the start() factory method creates correct event."""
        event = SegmentEvent.start(
            segment_id="seg_001",
            segment_type=SegmentType.TOOL_CALL,
            tool_name="weather_api"
        )
        
        assert event.event_type == SegmentEventType.START
        assert event.segment_id == "seg_001"
        assert event.segment_type == SegmentType.TOOL_CALL
        assert event.payload == {"metadata": {"tool_name": "weather_api"}}

    def test_start_factory_no_metadata(self):
        """Test start() factory with no metadata."""
        event = SegmentEvent.start(
            segment_id="seg_002",
            segment_type=SegmentType.TEXT
        )
        
        assert event.event_type == SegmentEventType.START
        assert event.segment_id == "seg_002"
        assert event.segment_type == SegmentType.TEXT
        assert event.payload == {}

    def test_content_factory(self):
        """Test the content() factory method creates correct event."""
        event = SegmentEvent.content(
            segment_id="seg_001",
            delta="Hello world"
        )
        
        assert event.event_type == SegmentEventType.CONTENT
        assert event.segment_id == "seg_001"
        assert event.segment_type is None
        assert event.payload == {"delta": "Hello world"}

    def test_end_factory(self):
        """Test the end() factory method creates correct event."""
        event = SegmentEvent.end(segment_id="seg_001")
        
        assert event.event_type == SegmentEventType.END
        assert event.segment_id == "seg_001"
        assert event.segment_type is None
        assert event.payload == {}

    def test_to_dict_start_event(self):
        """Test serialization of START event includes segment_type."""
        event = SegmentEvent.start(
            segment_id="seg_001",
            segment_type=SegmentType.FILE,
            path="/tmp/test.py"
        )
        
        result = event.to_dict()
        
        assert result == {
            "type": "SEGMENT_START",
            "segment_id": "seg_001",
            "segment_type": "file",
            "payload": {"metadata": {"path": "/tmp/test.py"}}
        }

    def test_to_dict_content_event(self):
        """Test serialization of CONTENT event excludes segment_type."""
        event = SegmentEvent.content(segment_id="seg_001", delta="code here")
        
        result = event.to_dict()
        
        assert result == {
            "type": "SEGMENT_CONTENT",
            "segment_id": "seg_001",
            "payload": {"delta": "code here"}
        }
        assert "segment_type" not in result

    def test_to_dict_end_event(self):
        """Test serialization of END event."""
        event = SegmentEvent.end(segment_id="seg_001")
        
        result = event.to_dict()
        
        assert result == {
            "type": "SEGMENT_END",
            "segment_id": "seg_001",
            "payload": {}
        }
