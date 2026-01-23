"""
Unit tests for XmlPatchFileToolParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.xml_patch_file_tool_parsing_state import XmlPatchFileToolParsingState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestXmlPatchFileToolParsingState:
    """Tests for XmlPatchFileToolParsingState functionality."""

    def test_parses_patch_file_tool(self):
        """Standard <tool name="patch_file"> is parsed correctly."""
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        content = (
            "<arguments>"
            "<arg name='path'>/tmp/test.py</arg>"
            "<arg name='patch'>@@ -1,3 +1,4 @@\n+new line</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)
        
        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Check START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.PATCH_FILE
        # Verify correctness: Path SHOULD be in start metadata now
        metadata = start_events[0].payload.get("metadata", {})
        assert metadata.get("path") == "/tmp/test.py"
        
        # Check CONTENT events - Should contain ONLY the patch content, not XML tags
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "@@ -1,3 +1,4 @@" in full_content
        assert "+new line" in full_content
        assert "<arg" not in full_content
        
        # Check END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_segment_type_is_patch_file(self):
        """Ensures the segment type is PATCH_FILE, not TOOL_CALL or WRITE_FILE."""
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        state = XmlPatchFileToolParsingState(ctx, signature)
        assert state.SEGMENT_TYPE == SegmentType.PATCH_FILE

    def test_incremental_streaming_fragmented(self):
        """
        Verifies that content is correctly extracted even when the XML tags 
        arrive in fragmented chunks.
        """
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        
        # Simulate the stream arriving in small chunks
        chunks = [
            "<argu", "ments><arg name", "='path'>/tmp/frag.py</arg>",
            "<arg name='pat", "ch'>",
            "@@ -1 +1 @@\n-old", "\n+new</arg",
            "></arguments></tool>"
        ]
        
        ctx.append(signature)
        state = XmlPatchFileToolParsingState(ctx, signature)
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
        assert "@@ -1 +1 @@" in full_content
        assert "-old" in full_content
        assert "+new" in full_content
        assert "<arg" not in full_content
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_deferred_start_event_streaming(self):
        """
        Verifies that the SEGMENT_START event is deferred until the path 
        argument is fully available in the stream.
        """
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state
        
        # Chunk 1: Just the opening structure
        ctx.append('<tool name="patch_file"><arguments>')
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
        
        # Chunk 3: Patch content
        ctx.append("<arg name='patch'>@@ diff @@</arg></arguments></tool>")
        state.run()
        
        # Verify content followed
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        assert len(content_events) > 0
        assert "@@ diff @@" in "".join(e.payload["delta"] for e in content_events)

    def test_swallows_closing_tags(self):
        """
        Verifies that </arguments> and </tool> are swallowed and not emitted as text.
        """
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state
        
        # Complete tool call
        full_text = (
            "<arguments>"
            "<arg name='path'>/tmp/test.py</arg>"
            "<arg name='patch'>patch data</arg>"
            "</arguments></tool>"
        )
        # Add some text AFTER the tool
        full_text += "Post tool text"
        
        ctx.append(full_text)
        state.run()  # Should consume everything including closing tags
        
        # Run until empty
        while ctx.has_more_chars():
            ctx.current_state.run()
            
        events = ctx.get_and_clear_events()
        
        full_dump = "".join(e.payload.get("delta", "") for e in events if e.event_type == SegmentEventType.CONTENT)
        
        assert "patch data" in full_dump
        assert "Post tool text" in full_dump
        assert "</arguments>" not in full_dump
        assert "</tool>" not in full_dump

    def test_patch_markers_stream_raw(self):
        """Patch markers stream only the raw text between markers."""
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        content = (
            "<arguments>"
            "<arg name='path'>/tmp/marker.py</arg>"
            "<arg name='patch'>"
            "__START_PATCH__\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,2 +1,3 @@\n"
            " existing\n"
            "+new line\n"
            "__END_PATCH__"
            "</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)

        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)

        assert "__START_PATCH__" not in full_content
        assert "__END_PATCH__" not in full_content
        assert "--- a/file.py" in full_content
        assert "+++ b/file.py" in full_content
        assert "+new line" in full_content

        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_patch_markers_split_across_chunks(self):
        """Patch markers can be split across streaming chunks."""
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        chunks = [
            "<arguments><arg name='path'>/tmp/chunk.py</arg><arg name='patch'>__STAR",
            "T_PATCH__--- file.py\n+new\n__END",
            "_PATCH__</arg></arguments></tool>",
        ]

        ctx.append(signature)
        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state

        for chunk in chunks:
            ctx.append(chunk)
            state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)

        assert "__START_PATCH__" not in full_content
        assert "__END_PATCH__" not in full_content
        assert "--- file.py" in full_content
        assert "+new" in full_content

        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_unified_diff_with_special_characters(self):
        """Unified diff content with special XML characters is handled correctly."""
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        content = (
            "<arguments>"
            "<arg name='path'>/tmp/special.py</arg>"
            "<arg name='patch'>"
            "__START_PATCH__\n"
            "--- a/code.py\n"
            "+++ b/code.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-if x < 10 and y > 5:\n"
            "+if x <= 10 and y >= 5:\n"
            "__END_PATCH__"
            "</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)

        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)

        # The < and > characters should be preserved
        assert "x < 10" in full_content
        assert "y > 5" in full_content

        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_nested_end_patch_marker_not_followed_by_arg_close(self):
        """
        Patch content containing __END_PATCH__ NOT followed by </arg> should be 
        treated as regular content, not as the sentinel.
        """
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        content = (
            "<arguments>"
            "<arg name='path'>/tmp/nested.py</arg>"
            "<arg name='patch'>"
            "__START_PATCH__\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -10,3 +10,3 @@\n"
            "-# Old comment\n"
            "+# Note: Do not remove __END_PATCH__ marker\n"
            " code()\n"
            "__END_PATCH__"
            "</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)

        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)

        # The nested __END_PATCH__ marker should be preserved in the content
        assert "+# Note: Do not remove __END_PATCH__ marker" in full_content
        assert "code()" in full_content
        
        # But the final sentinel should NOT appear
        assert "__START_PATCH__" not in full_content
        # The final __END_PATCH__ (before </arg>) should be stripped
        assert full_content.rstrip().endswith("code()")

        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_nested_end_patch_streaming_fragmented(self):
        """
        Nested __END_PATCH__ handling works correctly when content arrives 
        in fragmented chunks.
        """
        ctx = ParserContext()
        signature = '<tool name="patch_file">'
        
        # Simulate fragmented streaming where __END_PATCH__ is split
        chunks = [
            "<arguments><arg name='path'>/tmp/frag.py</arg><arg name='patch'>",
            "__START_PATCH__\n",
            "-old line\n",
            "+new line with __END_PA",  # Partial marker in content
            "TCH__ inside\n",  # Complete the false marker
            "__END_PA",  # Partial real marker
            "TCH__",  # Complete real marker
            "\n</arg>",  # Whitespace + close tag
            "</arguments></tool>",
        ]

        ctx.append(signature)
        state = XmlPatchFileToolParsingState(ctx, signature)
        ctx.current_state = state

        for chunk in chunks:
            ctx.append(chunk)
            state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)

        # The nested __END_PATCH__ in the content should be preserved
        assert "+new line with __END_PATCH__ inside" in full_content
        assert "-old line" in full_content
        
        # Sentinels should NOT appear
        assert "__START_PATCH__" not in full_content
        assert full_content.count("__END_PATCH__") == 1

        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
