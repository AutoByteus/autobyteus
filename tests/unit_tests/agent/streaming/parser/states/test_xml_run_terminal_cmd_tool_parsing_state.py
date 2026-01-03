"""
Unit tests for XmlRunTerminalCmdToolParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.states.xml_run_terminal_cmd_tool_parsing_state import XmlRunTerminalCmdToolParsingState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestXmlRunTerminalCmdToolParsingState:
    """Tests for XmlRunTerminalCmdToolParsingState functionality."""

    def test_parses_run_terminal_cmd_tool(self):
        """Standard <tool name="run_terminal_cmd"> is parsed correctly."""
        ctx = ParserContext()
        signature = '<tool name="run_terminal_cmd">'
        content = (
            "<arguments>"
            "<arg name='command'>ls -la</arg>"
            "</arguments></tool>"
        )
        ctx.append(signature + content)
        
        state = XmlRunTerminalCmdToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Check START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.RUN_TERMINAL_CMD
        
        # Check CONTENT events - Should contain ONLY the command
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "ls -la" in full_content
        assert "<arg" not in full_content
        
        # Check END event and ARGUMENTS
        final_meta = ctx.get_current_segment_metadata()
        args = final_meta.get("arguments", {})
        assert args.get("command") == "ls -la"

    def test_segment_type_is_run_terminal_cmd(self):
        """Ensures the segment type is RUN_TERMINAL_CMD."""
        ctx = ParserContext()
        signature = '<tool name="run_terminal_cmd">'
        state = XmlRunTerminalCmdToolParsingState(ctx, signature)
        assert state.SEGMENT_TYPE == SegmentType.RUN_TERMINAL_CMD

    def test_incremental_streaming_fragmented(self):
        """
        Verifies command extraction with fragmented XML tag delivery.
        """
        ctx = ParserContext()
        signature = '<tool name="run_terminal_cmd">'
        
        # Fragmented stream
        chunks = [
            "<arguments><arg ", "name='command'>",
            "ls ", "-la /var/log",
            "</arg></arguments></tool>"
        ]
        
        ctx.append(signature)
        state = XmlRunTerminalCmdToolParsingState(ctx, signature)
        ctx.current_state = state
        
        for chunk in chunks:
            ctx.append(chunk)
            state.run()
            
        events = ctx.get_and_clear_events()
        
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        full_content = "".join(e.payload.get("delta", "") for e in content_events)
        
        assert "ls -la /var/log" in full_content
        assert "<arg" not in full_content
        
        final_meta = ctx.get_current_segment_metadata()
        args = final_meta.get("arguments", {})
        assert args.get("command") == "ls -la /var/log"

    def test_swallows_closing_tags(self):
        """
        Verifies that </arguments> and </tool> are swallowed and not emitted as text
        for run_terminal_cmd.
        """
        ctx = ParserContext()
        signature = '<tool name="run_terminal_cmd">'
        state = XmlRunTerminalCmdToolParsingState(ctx, signature)
        ctx.current_state = state
        
        # Complete tool call
        full_text = (
            "<arguments>"
            "<arg name='command'>echo test</arg>"
            "</arguments></tool>"
        )
        # Add some text AFTER the tool
        full_text += "Post command text"
        
        ctx.append(full_text)
        state.run() # Should consume everything including closing tags
        
        # Run any subsequent state processing
        while ctx.has_more_chars():
            ctx.current_state.run()
            
        events = ctx.get_and_clear_events()
        
        full_dump = "".join(e.payload.get("delta", "") for e in events if e.event_type == SegmentEventType.CONTENT)
        
        assert "echo test" in full_dump
        assert "Post command text" in full_dump
        assert "</arguments>" not in full_dump
        assert "</tool>" not in full_dump
