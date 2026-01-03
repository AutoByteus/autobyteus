"""
Unit tests for XmlToolParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext, ParserConfig
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.xml_tool_parsing_state import XmlToolParsingState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestXmlToolParsingStateBasics:
    """Tests for basic XmlToolParsingState functionality."""

    def test_simple_tool_call(self):
        """Simple tool call is parsed correctly."""
        ctx = ParserContext()
        signature = "<tool name='weather'>"
        ctx.append(signature + "<arguments><arg name='city'>NYC</arg></arguments></tool>after")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Find START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.TOOL_CALL
        assert start_events[0].payload.get("metadata", {}).get("tool_name") == "weather"
        
        # Should transition to TextState
        assert isinstance(ctx.current_state, TextState)

    def test_tool_with_double_quotes(self):
        """Tool tag with double quotes works."""
        ctx = ParserContext()
        signature = '<tool name="get_weather">'
        ctx.append(signature + "<arguments><arg name='location'>Paris</arg></arguments></tool>")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert start_events[0].payload.get("metadata", {}).get("tool_name") == "get_weather"

    def test_tool_without_name_becomes_text(self):
        """Tool tag without name attribute is treated as text."""
        ctx = ParserContext()
        signature = "<tool>"  # No name
        ctx.append(signature + "content</tool>")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        # Should emit as text (no tool segment)
        tool_starts = [e for e in events if e.event_type == SegmentEventType.START and e.segment_type == SegmentType.TOOL_CALL]
        assert len(tool_starts) == 0


class TestXmlToolParsingStateArguments:
    """Tests for argument extraction."""

    def test_single_argument_extracted(self):
        """Single argument is correctly extracted."""
        ctx = ParserContext()
        signature = "<tool name='test'>"
        ctx.append(signature + "<arguments><arg name='path'>/test/file.py</arg></arguments></tool>")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        # The parsed arguments should be in the metadata
        # We can check this by looking at the current segment metadata
        events = ctx.get_and_clear_events()
        # Arguments should be in the content or metadata

    def test_multiple_arguments_extracted(self):
        """Multiple arguments are correctly extracted."""
        ctx = ParserContext()
        signature = "<tool name='write_file'>"
        content = "<arguments><arg name='path'>/test.py</arg><arg name='content'>print('hello')</arg></arguments></tool>"
        ctx.append(signature + content)
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        # Should complete successfully
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_named_arguments_with_items(self):
        """Named <arg> tags and <item> arrays are parsed into structured arguments."""
        ctx = ParserContext()
        signature = "<tool name='update_task_status'>"
        content = (
            "<arguments>"
            "<arg name='task_name'>task_a</arg>"
            "<arg name='deliverables'>"
            "<item>"
            "<arg name='file_path'>src/main.py</arg>"
            "<arg name='summary'>Final version</arg>"
            "</item>"
            "</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)

        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()

        events = ctx.get_and_clear_events()
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
        arguments = end_events[0].payload.get("metadata", {}).get("arguments", {})
        assert arguments["task_name"] == "task_a"
        assert arguments["deliverables"] == [
            {"file_path": "src/main.py", "summary": "Final version"}
        ]

    def test_arguments_with_unescaped_lt_in_text(self):
        """Text containing '<' is sanitized so XML parsing still succeeds."""
        ctx = ParserContext()
        signature = "<tool name='create_tasks'>"
        content = (
            "<arguments>"
            "<arg name='tasks'>"
            "<item>"
            "<arg name='description'>Handle n <= 0 case</arg>"
            "</item>"
            "</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)

        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()

        events = ctx.get_and_clear_events()
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
        arguments = end_events[0].payload.get("metadata", {}).get("arguments", {})
        assert arguments["tasks"] == [{"description": "Handle n <= 0 case"}]


class TestXmlToolParsingStateStreaming:
    """Tests for streaming tool content."""

    def test_tool_content_complete(self):
        """Tool content is fully parsed in one pass."""
        ctx = ParserContext()
        signature = "<tool name='slow_api'>"
        full_content = signature + "<arguments><arg name='query'>testing</arg></arguments></tool>done"
        ctx.append(full_content)
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        all_events = ctx.get_and_clear_events()
        
        # Should have completed
        end_events = [e for e in all_events if e.event_type == SegmentEventType.END]
        assert len(end_events) >= 1
        
        # Should be in TextState
        assert isinstance(ctx.current_state, TextState)


class TestXmlToolParsingStateFinalize:
    """Tests for finalize behavior."""

    def test_finalize_incomplete_tool(self):
        """Incomplete tool at stream end is closed properly."""
        ctx = ParserContext()
        signature = "<tool name='test'>"
        ctx.append(signature + "<arguments><arg>val")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        # Finalize without closing tag
        state.finalize()
        
        events = ctx.get_and_clear_events()
        # Should have END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) >= 1


class TestXmlToolParsingStateArgNameStreaming:
    """Tests for arg_name context in CONTENT events."""

    def test_content_events_include_arg_name(self):
        """CONTENT events include arg_name for argument values."""
        ctx = ParserContext()
        signature = "<tool name='test'>"
        ctx.append(signature + "<arguments><arg name='path'>/test.py</arg></arguments></tool>")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        
        # Find content events with arg_name="path"
        path_content = [e for e in content_events if e.payload.get("arg_name") == "path"]
        assert len(path_content) > 0, "Should have content events with arg_name='path'"
        
        # Verify the path value is in the delta
        combined_path_delta = "".join(e.payload.get("delta", "") for e in path_content)
        assert "/test.py" in combined_path_delta

    def test_multiple_args_have_correct_arg_names(self):
        """Multiple arguments each have their correct arg_name in CONTENT events."""
        ctx = ParserContext()
        signature = "<tool name='write'>"
        content = "<arguments><arg name='path'>/a.py</arg><arg name='content'>hello</arg></arguments></tool>"
        ctx.append(signature + content)
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        
        # Find content events for each arg
        path_content = [e for e in content_events if e.payload.get("arg_name") == "path"]
        content_content = [e for e in content_events if e.payload.get("arg_name") == "content"]
        
        # Both should have content
        assert len(path_content) > 0, "Should have content events for 'path'"
        assert len(content_content) > 0, "Should have content events for 'content'"
        
        # Verify values
        path_delta = "".join(e.payload.get("delta", "") for e in path_content)
        content_delta = "".join(e.payload.get("delta", "") for e in content_content)
        assert "/a.py" in path_delta
        assert "hello" in content_delta

    def test_raw_marker_content_streams_with_arg_name(self):
        """Raw marker content streams with arg_name and markers are not emitted."""
        ctx = ParserContext()
        signature = "<tool name='write'>"
        content = (
            "<arguments><arg name='content'>"
            "__START_CONTENT__\n"
            "if x < y:\n  print('<div>')\n"
            "__END_CONTENT__"
            "</arg></arguments></tool>"
        )
        ctx.append(signature + content)
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        
        deltas = [e.payload.get("delta", "") for e in content_events]
        assert "__START_CONTENT__" not in "".join(deltas)
        assert "__END_CONTENT__" not in "".join(deltas)
        
        content_with_arg = [e for e in content_events if e.payload.get("arg_name") == "content"]
        combined = "".join(e.payload.get("delta", "") for e in content_with_arg)
        assert "if x < y:" in combined
        assert "<div>" in combined

    def test_raw_marker_split_across_chunks(self):
        """Raw marker close token split across chunks is handled correctly."""
        ctx = ParserContext()
        signature = "<tool name='write'>"
        part1 = signature + "<arguments><arg name='content'>__START_CONTENT__\nabc__END_"
        part2 = "CONTENT__</arg></arguments></tool>"
        ctx.append(part1)
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        ctx.append(part2)
        state.run()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content_with_arg = [e for e in content_events if e.payload.get("arg_name") == "content"]
        combined = "".join(e.payload.get("delta", "") for e in content_with_arg)
        assert "abc" in combined

    def test_raw_marker_start_split_across_chunks(self):
        """Raw marker start token split across chunks is handled correctly."""
        ctx = ParserContext()
        signature = "<tool name='write'>"
        part1 = signature + "<arguments><arg name='content'>__START_CO"
        part2 = "NTENT__\nabc__END_CONTENT__</arg></arguments></tool>"
        ctx.append(part1)
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        ctx.append(part2)
        state.run()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        deltas = "".join(e.payload.get("delta", "") for e in content_events)
        assert "__START_CONTENT__" not in deltas
        assert "__END_CONTENT__" not in deltas
        assert "abc" in deltas

    def test_arg_states_across_chunk_boundaries(self):
        """Argument boundary events are emitted across chunk boundaries."""
        ctx = ParserContext()
        signature = "<tool name='test'>"
        chunks = [
            signature + "<arguments><arg name='path'>/a",
            ".py</arg><arg name='content'>he",
            "llo</arg></arguments></tool>",
        ]
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        ctx.append(chunks[0])
        state.run()
        ctx.append(chunks[1])
        state.run()
        ctx.append(chunks[2])
        state.run()

        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        path_events = [e for e in content_events if e.payload.get("arg_name") == "path"]
        content_events_for_arg = [e for e in content_events if e.payload.get("arg_name") == "content"]
        assert any(e.payload.get("arg_state") == "start" for e in path_events)
        assert any(e.payload.get("arg_state") == "end" for e in path_events)
        combined_path = "".join(e.payload.get("delta", "") for e in path_events)
        assert "/a.py" in combined_path
        assert any(e.payload.get("arg_state") == "start" for e in content_events_for_arg)
        assert any(e.payload.get("arg_state") == "end" for e in content_events_for_arg)
        combined_content = "".join(e.payload.get("delta", "") for e in content_events_for_arg)
        assert "hello" in combined_content

    def test_arg_state_boundaries(self):
        """Argument start/delta/end states are emitted."""
        ctx = ParserContext()
        signature = "<tool name='test'>"
        ctx.append(signature + "<arguments><arg name='path'>/test.py</arg></arguments></tool>")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT and e.payload.get("arg_name") == "path"]
        states = [e.payload.get("arg_state") for e in content_events]
        assert "start" in states
        assert "delta" in states
        assert "end" in states

    def test_raw_marker_preserves_xml_like_text(self):
        """Raw markers protect XML-like text inside an argument."""
        ctx = ParserContext()
        signature = "<tool name='write'>"
        content = (
            "<arguments><arg name='content'>"
            "__START_CONTENT__\n"
            "literal </arg> and <arg name='x'>text</arg>\n"
            "__END_CONTENT__"
            "</arg></arguments></tool>"
        )
        ctx.append(signature + content)

        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()

        events = ctx.get_and_clear_events()
        end_event = next(e for e in events if e.event_type == SegmentEventType.END)
        arguments = end_event.payload.get("metadata", {}).get("arguments", {})
        assert "literal </arg> and <arg name='x'>text</arg>" in arguments.get("content", "")

    def test_arg_name_none_outside_args(self):
        """Content outside of argument tags has arg_name=None."""
        ctx = ParserContext()
        signature = "<tool name='test'>"
        # Whitespace before <arguments> is outside args
        ctx.append(signature + "  <arguments><arg name='path'>/test.py</arg></arguments></tool>")
        
        state = XmlToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        
        # Should have some content events with arg_name=None (whitespace before <arguments>)
        no_arg_content = [e for e in content_events if e.payload.get("arg_name") is None]
        assert len(no_arg_content) > 0, "Should have content events without arg_name"
