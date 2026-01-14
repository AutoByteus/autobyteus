"""
Unit tests for ApiToolCallStreamingResponseHandler.
"""
import pytest
from autobyteus.agent.streaming.handlers.api_tool_call_streaming_response_handler import (
    ApiToolCallStreamingResponseHandler,
)
from autobyteus.agent.streaming.segments.segment_events import (
    SegmentEvent,
    SegmentType,
    SegmentEventType,
)
from autobyteus.llm.utils.response_types import ChunkResponse
from autobyteus.llm.utils.tool_call_delta import ToolCallDelta


class TestApiToolCallStreamingResponseHandlerBasics:
    """Basic functionality tests."""

    def test_feed_text_emits_text_segment(self):
        """Text content creates TEXT segment events."""
        handler = ApiToolCallStreamingResponseHandler()
        events = handler.feed(ChunkResponse(content="Hello world"))
        
        assert len(events) == 2  # START + CONTENT
        assert events[0].event_type == SegmentEventType.START
        assert events[0].segment_type == SegmentType.TEXT
        assert events[1].event_type == SegmentEventType.CONTENT
        assert events[1].payload["delta"] == "Hello world"

    def test_feed_write_file_emits_write_file_segment(self):
        """write_file emits WRITE_FILE segment events in API tool call mode."""
        handler = ApiToolCallStreamingResponseHandler()

        events1 = handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                call_id="call_123",
                name="write_file",
                arguments_delta='{"path":"test.txt","content":"h'
            )]
        ))

        events2 = handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                arguments_delta='i"}'
            )]
        ))

        start_event = next(e for e in events1 if e.event_type == SegmentEventType.START)
        assert start_event.segment_type == SegmentType.WRITE_FILE
        assert start_event.payload["metadata"]["path"] == "test.txt"
        first_content = next(e for e in events1 if e.event_type == SegmentEventType.CONTENT)
        assert first_content.payload["delta"] == "h"
        assert events2[0].event_type == SegmentEventType.CONTENT
        assert events2[0].payload["delta"] == "i"

    def test_finalize_creates_invocation(self):
        """Finalize creates ToolInvocation from accumulated args."""
        handler = ApiToolCallStreamingResponseHandler()
        
        # Start tool
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                call_id="call_abc",
                name="write_file"
            )]
        ))
        
        # Stream args
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                arguments_delta='{"path": "hello.py", "content": "print()"}'
            )]
        ))
        
        # Finalize
        handler.finalize()
        
        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        assert invocations[0].name == "write_file"
        assert invocations[0].arguments == {"path": "hello.py", "content": "print()"}
        assert invocations[0].id == "call_abc"


class TestApiToolCallStreamingResponseHandlerParallel:
    """Tests for parallel tool calls."""

    def test_parallel_tool_calls(self):
        """Multiple tool calls tracked by index."""
        handler = ApiToolCallStreamingResponseHandler()
        
        # Both tools start
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[
                ToolCallDelta(index=0, call_id="call_write", name="write_file"),
                ToolCallDelta(index=1, call_id="call_bash", name="run_bash"),
            ]
        ))
        
        # Args for tool 0
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[
                ToolCallDelta(index=0, arguments_delta='{"path": "test.py"}'),
            ]
        ))
        
        # Args for tool 1
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[
                ToolCallDelta(index=1, arguments_delta='{"command": "python test.py"}'),
            ]
        ))
        
        handler.finalize()
        
        invocations = handler.get_all_invocations()
        assert len(invocations) == 2
        
        write_inv = next((i for i in invocations if i.name == "write_file"), None)
        bash_inv = next((i for i in invocations if i.name == "run_bash"), None)
        
        assert write_inv is not None
        assert bash_inv is not None
        assert write_inv.arguments == {"path": "test.py", "content": ""}
        assert bash_inv.arguments == {"command": "python test.py"}


class TestApiToolCallStreamingResponseHandlerFileStreaming:
    """Tests for file tool streaming behavior."""

    def test_patch_file_emits_patch_segment(self):
        handler = ApiToolCallStreamingResponseHandler()

        events1 = handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                call_id="call_patch",
                name="patch_file",
                arguments_delta='{"path":"a.txt","patch":"@@ -1 +1 @@'
            )]
        ))

        events2 = handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                arguments_delta='\\n-foo"}'
            )]
        ))

        start_event = next(e for e in events1 if e.event_type == SegmentEventType.START)
        assert start_event.segment_type == SegmentType.PATCH_FILE
        assert start_event.payload["metadata"]["path"] == "a.txt"
        first_content = next(e for e in events1 if e.event_type == SegmentEventType.CONTENT)
        assert first_content.payload["delta"] == "@@ -1 +1 @@"
        assert events2[0].payload["delta"] == "\n-foo"

    def test_write_file_defers_start_until_path_available(self):
        handler = ApiToolCallStreamingResponseHandler()

        events1 = handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                call_id="call_defer",
                name="write_file",
                arguments_delta='{"content":"Hello'
            )]
        ))

        # No start/content should emit before path is known.
        assert events1 == []

        events2 = handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                arguments_delta=' world","path":"deferred.txt"}'
            )]
        ))

        start_event = next(e for e in events2 if e.event_type == SegmentEventType.START)
        assert start_event.segment_type == SegmentType.WRITE_FILE
        assert start_event.payload["metadata"]["path"] == "deferred.txt"
        content_deltas = [
            e.payload["delta"]
            for e in events2
            if e.event_type == SegmentEventType.CONTENT
        ]
        assert "".join(content_deltas) == "Hello world"

    def test_write_file_decodes_escaped_content(self):
        handler = ApiToolCallStreamingResponseHandler()

        handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                call_id="call_write",
                name="write_file",
                arguments_delta='{"path":"a.txt","content":"hi\\\\'
            )]
        ))
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(
                index=0,
                arguments_delta='nthere"}'
            )]
        ))

        handler.finalize()

        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        assert invocations[0].arguments == {"path": "a.txt", "content": "hi\\nthere"}


class TestApiToolCallStreamingResponseHandlerCallbacks:
    """Callback tests."""

    def test_on_segment_event_called(self):
        """on_segment_event callback is invoked for each event."""
        received = []
        
        handler = ApiToolCallStreamingResponseHandler(
            on_segment_event=lambda e: received.append(e)
        )
        handler.feed(ChunkResponse(content="Hello"))
        handler.finalize()
        
        assert len(received) > 0
        assert all(isinstance(e, SegmentEvent) for e in received)

    def test_on_tool_invocation_called(self):
        """on_tool_invocation callback is invoked when invocation created."""
        invocations = []
        
        handler = ApiToolCallStreamingResponseHandler(
            on_tool_invocation=lambda inv: invocations.append(inv)
        )
        
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(index=0, call_id="call_x", name="test")]
        ))
        handler.feed(ChunkResponse(
            content="",
            tool_calls=[ToolCallDelta(index=0, arguments_delta='{}')]
        ))
        handler.finalize()
        
        assert len(invocations) == 1
        assert invocations[0].name == "test"


class TestApiToolCallStreamingResponseHandlerReset:
    """Reset functionality tests."""

    def test_reset_clears_state(self):
        """Reset allows handler reuse."""
        handler = ApiToolCallStreamingResponseHandler()
        
        handler.feed(ChunkResponse(content="test"))
        handler.finalize()
        
        assert len(handler.get_all_events()) > 0
        
        handler.reset()
        
        assert len(handler.get_all_events()) == 0
        assert len(handler.get_all_invocations()) == 0
        
        # Can feed again
        handler.feed(ChunkResponse(content="new data"))
        handler.finalize()
        assert len(handler.get_all_events()) > 0

    def test_feed_after_finalize_raises(self):
        """Feeding after finalize raises error."""
        handler = ApiToolCallStreamingResponseHandler()
        handler.finalize()
        
        with pytest.raises(RuntimeError):
            handler.feed(ChunkResponse(content="data"))
