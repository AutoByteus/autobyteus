"""
Unit tests for the XmlTagInitializationState class.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext, ParserConfig
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.xml_tag_initialization_state import XmlTagInitializationState
from autobyteus.agent.streaming.parser.states.file_parsing_state import FileParsingState
from autobyteus.agent.streaming.parser.states.bash_parsing_state import BashParsingState
from autobyteus.agent.streaming.parser.states.tool_parsing_state import ToolParsingState
from autobyteus.agent.streaming.parser.states.iframe_parsing_state import IframeParsingState
from autobyteus.agent.streaming.parser.events import SegmentEventType


class TestXmlTagInitConstructor:
    """Tests for XmlTagInitializationState constructor."""

    def test_consumes_less_than(self):
        """Constructor consumes the '<' character."""
        ctx = ParserContext()
        ctx.append("<tag>")
        
        # Position starts at 0
        assert ctx.get_position() == 0
        
        state = XmlTagInitializationState(ctx)
        
        # After constructor, position should be 1 (consumed '<')
        assert ctx.get_position() == 1


class TestXmlTagInitFileDetection:
    """Tests for <file tag detection."""

    def test_file_tag_transitions_to_file_state(self):
        """<file path="..."> triggers transition to FileParsingState."""
        ctx = ParserContext()
        ctx.append('<file path="/test.py">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, FileParsingState)

    def test_file_tag_case_insensitive(self):
        """<FILE (uppercase) also triggers FileParsingState."""
        ctx = ParserContext()
        ctx.append('<FILE path="/test.py">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, FileParsingState)



class TestXmlTagInitBashDetection:
    """Tests for <bash> tag detection."""

    def test_bash_tag_transitions_to_bash_state(self):
        """<bash> triggers transition to BashParsingState."""
        ctx = ParserContext()
        ctx.append("<bash>command</bash>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, BashParsingState)

    def test_bash_with_attributes(self):
        """<bash description='test'> also triggers BashParsingState."""
        ctx = ParserContext()
        ctx.append("<bash description='test'>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, BashParsingState)


class TestXmlTagInitToolDetection:
    """Tests for <tool> tag detection."""

    def test_tool_tag_transitions_to_tool_state(self):
        """<tool> triggers transition to ToolParsingState when parsing enabled."""
        ctx = ParserContext()  # parse_tool_calls=True by default
        ctx.append("<tool name='test'>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, ToolParsingState)

    def test_tool_tag_disabled_emits_text(self):
        """<tool> is treated as text when parse_tool_calls=False."""
        config = ParserConfig(parse_tool_calls=False)
        ctx = ParserContext(config)
        ctx.append("<tool name='test'>more text")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should transition back to TextState
        assert isinstance(ctx.current_state, TextState)
        
        # The tag should be emitted as text
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        assert any("<tool name='test'>" in e.payload.get("delta", "") for e in content_events)


class TestXmlTagInitDoctypeDetection:
    """Tests for <!doctype html> detection."""

    def test_doctype_transitions_to_iframe_state(self):
        """<!doctype html> triggers transition to IframeParsingState."""
        ctx = ParserContext()
        ctx.append("<!doctype html><html>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, IframeParsingState)

    def test_doctype_case_insensitive(self):
        """<!DOCTYPE HTML> also triggers IframeParsingState."""
        ctx = ParserContext()
        ctx.append("<!DOCTYPE HTML><html>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, IframeParsingState)


class TestXmlTagInitUnknownTags:
    """Tests for unknown/invalid tags."""

    def test_unknown_tag_emits_text(self):
        """Unknown tags like <div> are emitted as text."""
        ctx = ParserContext()
        ctx.append("<div>content")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should return to TextState
        assert isinstance(ctx.current_state, TextState)
        
        # The partial buffer is emitted when pattern fails
        # <d doesn't match any known prefix, so "<d" is emitted
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        # The buffer at point of failure is "<d"
        assert any("<d" in e.payload.get("delta", "") for e in content_events)

    def test_malformed_start_emits_text(self):
        """<xyz (not a known prefix) immediately reverts to text."""
        ctx = ParserContext()
        ctx.append("<xyz>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, TextState)


class TestXmlTagInitPartialBuffer:
    """Tests for partial/incomplete tags."""

    def test_partial_file_waits_for_more(self):
        """Partial '<fil' waits for more characters."""
        ctx = ParserContext()
        ctx.append("<fil")  # Incomplete - could be <file
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        # State should still be XmlTagInitializationState (waiting)
        # Actually, after run() with exhausted buffer, we stay in same state
        # unless we explicitly transition
        
        # No events should be emitted yet
        events = ctx.get_and_clear_events()
        assert len(events) == 0


class TestXmlTagInitFinalize:
    """Tests for finalize behavior."""

    def test_finalize_emits_buffered_content(self):
        """Finalize emits any buffered tag content as text."""
        ctx = ParserContext()
        ctx.append("<tool")  # Incomplete tag when stream ends
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()  # Consumes buffer but doesn't complete
        
        # Finalize should emit the incomplete tag as text
        state.finalize()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        assert any("<tool" in e.payload.get("delta", "") for e in content_events)
