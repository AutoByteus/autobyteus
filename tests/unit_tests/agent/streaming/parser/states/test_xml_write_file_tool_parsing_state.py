"""
Unit tests for XmlWriteFileToolParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.xml_write_file_tool_parsing_state import XmlWriteFileToolParsingState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestXmlWriteFileToolParsingState:
    """Tests for XmlWriteFileToolParsingState functionality."""

    def test_parses_write_file_tool(self):
        """Standard <tool name="write_file"> is parsed correctly."""
        ctx = ParserContext()
        signature = '<tool name="write_file">'
        content = (
            "<arguments>"
            "<arg name='path'>/tmp/test.py</arg>"
            "<arg name='content'>print('hello')</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)
        
        state = XmlWriteFileToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Check START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.WRITE_FILE
        # Verify correctness: Path SHOULD be in start metadata now
        metadata = start_events[0].payload.get("metadata", {})
        assert metadata.get("path") == "/tmp/test.py"
        
        # Check CONTENT events - Should contain ONLY the content, not XML tags
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "print('hello')" in full_content
        assert "<arg" not in full_content
        
        # Check END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_segment_type_is_write_file(self):
        """Ensures the segment type is WRITE_FILE, not TOOL_CALL."""
        ctx = ParserContext()
        signature = '<tool name="write_file">'
        state = XmlWriteFileToolParsingState(ctx, signature)
        assert state.SEGMENT_TYPE == SegmentType.WRITE_FILE

    def test_incremental_streaming_fragmented(self):
        """
        Verifies that content is correctly extracted even when the XML tags 
        arrive in fragmented chunks.
        """
        ctx = ParserContext()
        signature = '<tool name="write_file">'
        
        # Simulate the stream arriving in small chunks
        chunks = [
            "<argu", "ments><arg name", "='path'>/tmp/frag.py</arg>",
            "<arg name='con", "tent'>",
            "print('frag", "mented')</arg",
            "></arguments></tool>"
        ]
        
        ctx.append(signature)
        state = XmlWriteFileToolParsingState(ctx, signature)
        ctx.current_state = state
        
        # Run state for each chunk
        for chunk in chunks:
            ctx.append(chunk)
            state.run()
            
        events = ctx.get_and_clear_events()
        
        # Check CONTENT events
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)
        
        # Expect clean content
        assert "print('fragmented')" in full_content
        assert "<arg" not in full_content
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_deferred_start_event_streaming(self):
        """
        Verifies that the SEGMENT_START event is deferred until the path 
        argument is fully available in the stream.
        """
        ctx = ParserContext()
        signature = '<tool name="write_file">'
        state = XmlWriteFileToolParsingState(ctx, signature)
        ctx.current_state = state
        
        # Chunk 1: Just the opening structure
        ctx.append('<tool name="write_file"><arguments>')
        state.run()
        
        # Expectation: NO events yet because we are waiting for path
        events = ctx.get_events()
        assert len(events) == 0
        
        # Chunk 2: The path argument
        ctx.append("<arg name='path'>/tmp/delayed.py</arg>")
        state.run()
        
        # Expectation: NOW we should have the START event with the path
        events = ctx.get_and_clear_events()
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].payload["metadata"]["path"] == "/tmp/delayed.py"
        
        # Chunk 3: Content
        ctx.append("<arg name='content'>data</arg></arguments></tool>")
        state.run()
        
        # Verify content followed
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        assert len(content_events) > 0
        assert "data" in "".join(e.payload["delta"] for e in content_events)

    def test_swallows_closing_tags(self):
        """
        Verifies that </arguments> and </tool> are swallowed and not emitted as text.
        """
        ctx = ParserContext()
        signature = '<tool name="write_file">'
        state = XmlWriteFileToolParsingState(ctx, signature)
        ctx.current_state = state
        
        # Complete tool call
        full_text = (
            "<arguments>"
            "<arg name='path'>/tmp/test.py</arg>"
            "<arg name='content'>data</arg>"
            "</arguments></tool>"
        )
        # Add some text AFTER the tool
        full_text += "Post tool text"
        
        ctx.append(full_text)
        state.run() # Should consume everything including closing tags
        
        # If run() transitions to TextState, we need to run that too to see "Post tool text"
        # Since we append text segments directly in _handle_swallowing via parser context...
        # Wait, context.append_text_segment implies we are updating the current text segment.
        # But if we transitioned to TextState, future runs will handle it.
        # If we injected it *manually*, it might appear as EVENTS differently.
        
        # Let's run until empty
        while ctx.has_more_chars():
            ctx.current_state.run()
            
        events = ctx.get_and_clear_events()
        
        # Check that we have a CONTENT event for "data" and a CONTENT event for "Post tool text"
        # BUT NO content event for "</arguments></tool>"
        
        all_content = "".join(
            e.payload.get("delta", "") 
            for e in events 
            if e.event_type == SegmentEventType.CONTENT 
            and e.segment_type != SegmentType.WRITE_FILE
        )
        
        # Filter for TEXT segments specifically if possible, or just check global content dump
        # SegmentType.WRITE_FILE events:
        wf_content = "".join(
            e.payload.get("delta", "")
            for e in events
            if e.event_type == SegmentEventType.CONTENT
            and e.segment_id.startswith("write_file") # or we check internal event type
        )
        
        # We assume the implementation uses existing segment ID for content emission
        # Check simply for presence/absence
        
        full_dump = "".join(e.payload.get("delta", "") for e in events if e.event_type == SegmentEventType.CONTENT)
        
        assert "data" in full_dump
        assert "Post tool text" in full_dump
        assert "</arguments>" not in full_dump
        assert "</tool>" not in full_dump

    def test_content_markers_stream_raw(self):
        """Content markers stream only the raw text between markers."""
        ctx = ParserContext()
        signature = '<tool name="write_file">'
        content = (
            "<arguments>"
            "<arg name='path'>/tmp/marker.py</arg>"
            "<arg name='content'>"
            "__START_CONTENT__\n"
            "print('<div>')\n"
            "<arg name=\"x\">y</arg>\n"
            "__END_CONTENT__"
            "</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)

        state = XmlWriteFileToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)

        assert "__START_CONTENT__" not in full_content
        assert "__END_CONTENT__" not in full_content
        assert "<arg name=\"x\">y</arg>" in full_content
        assert full_content == "print('<div>')\n<arg name=\"x\">y</arg>\n"

        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_content_markers_split_across_chunks(self):
        """Content markers can be split across streaming chunks."""
        ctx = ParserContext()
        signature = '<tool name="write_file">'
        chunks = [
            "<arguments><arg name='path'>/tmp/chunk.py</arg><arg name='content'>__STAR",
            "T_CONTENT__print('hi')\n<arg>ok</arg>\n__END",
            "_CONTENT__</arg></arguments></tool>",
        ]

        ctx.append(signature)
        state = XmlWriteFileToolParsingState(ctx, signature)
        ctx.current_state = state

        for chunk in chunks:
            ctx.append(chunk)
            state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)

        assert "__START_CONTENT__" not in full_content
        assert "__END_CONTENT__" not in full_content
        assert full_content == "print('hi')\n<arg>ok</arg>\n"

        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
