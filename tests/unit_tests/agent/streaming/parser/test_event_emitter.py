"""
Unit tests for the EventEmitter class.
"""
import pytest
from autobyteus.agent.streaming.parser.event_emitter import EventEmitter
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestEventEmitterBasics:
    """Tests for basic EventEmitter functionality."""

    def test_emit_segment_lifecycle(self):
        """Full segment lifecycle emits correct events."""
        emitter = EventEmitter()
        
        # Start segment
        seg_id = emitter.emit_segment_start(SegmentType.TEXT)
        assert seg_id == "seg_1"
        assert emitter.get_current_segment_id() == "seg_1"
        
        # Emit content
        emitter.emit_segment_content("Hello")
        assert emitter.get_current_segment_content() == "Hello"
        
        # End segment
        ended_id = emitter.emit_segment_end()
        assert ended_id == "seg_1"
        assert emitter.get_current_segment_id() is None
        
        # Check events
        events = emitter.get_and_clear_events()
        assert len(events) == 3

    def test_unique_segment_ids(self):
        """Each segment gets a unique ID."""
        emitter = EventEmitter()
        
        id1 = emitter.emit_segment_start(SegmentType.TEXT)
        emitter.emit_segment_end()
        
        id2 = emitter.emit_segment_start(SegmentType.FILE)
        emitter.emit_segment_end()
        
        assert id1 == "seg_1"
        assert id2 == "seg_2"

    def test_emit_content_without_segment_raises(self):
        """Emitting content without active segment raises error."""
        emitter = EventEmitter()
        
        with pytest.raises(RuntimeError, match="Cannot emit content"):
            emitter.emit_segment_content("test")

    def test_emit_end_without_segment_returns_none(self):
        """Ending without active segment returns None."""
        emitter = EventEmitter()
        result = emitter.emit_segment_end()
        assert result is None


class TestEventEmitterMetadata:
    """Tests for metadata management."""

    def test_emit_with_metadata(self):
        """Segment start with metadata."""
        emitter = EventEmitter()
        emitter.emit_segment_start(SegmentType.FILE, path="/test.py")
        
        metadata = emitter.get_current_segment_metadata()
        assert metadata == {"path": "/test.py"}

    def test_update_metadata(self):
        """Metadata can be updated."""
        emitter = EventEmitter()
        emitter.emit_segment_start(SegmentType.TOOL_CALL, tool_name="test")
        emitter.update_current_segment_metadata(arg1="value1")
        
        metadata = emitter.get_current_segment_metadata()
        assert metadata == {"tool_name": "test", "arg1": "value1"}


class TestEventEmitterTextHelper:
    """Tests for text segment helper."""

    def test_append_text_segment(self):
        """append_text_segment emits full lifecycle."""
        emitter = EventEmitter()
        emitter.append_text_segment("Hello World")
        
        events = emitter.get_and_clear_events()
        assert len(events) == 3
        assert events[0].event_type == SegmentEventType.START
        assert events[1].event_type == SegmentEventType.CONTENT
        assert events[2].event_type == SegmentEventType.END

    def test_append_empty_text(self):
        """Empty text emits nothing."""
        emitter = EventEmitter()
        emitter.append_text_segment("")
        
        events = emitter.get_and_clear_events()
        assert len(events) == 0
