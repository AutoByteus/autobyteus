"""
Unit tests for XmlToolParsingState.
"""
from autobyteus.agent.streaming.parser.parser_context import ParserContext
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

    def test_tool_content_streams_raw_xml(self):
        """Tool content is streamed raw; arguments are not parsed in metadata."""
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
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "<arguments>" in full_content
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
        metadata = end_events[0].payload.get("metadata", {})
        assert "arguments" not in metadata


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
