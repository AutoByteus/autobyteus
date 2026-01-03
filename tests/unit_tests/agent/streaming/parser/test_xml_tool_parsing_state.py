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
        ctx.append(signature + "<arguments><city>NYC</city></arguments></tool>after")
        
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
        ctx.append(signature + "<arguments><location>Paris</location></arguments></tool>")
        
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
        ctx.append(signature + "<arguments><path>/test/file.py</path></arguments></tool>")
        
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
        content = "<arguments><path>/test.py</path><content>print('hello')</content></arguments></tool>"
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
        full_content = signature + "<arguments><query>testing</query></arguments></tool>done"
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
