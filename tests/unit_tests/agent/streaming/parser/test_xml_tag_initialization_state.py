"""
Unit tests for the XmlTagInitializationState class.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext, ParserConfig
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.xml_tag_initialization_state import XmlTagInitializationState
from autobyteus.agent.streaming.parser.states.custom_xml_tag_write_file_parsing_state import CustomXmlTagWriteFileParsingState
from autobyteus.agent.streaming.parser.states.custom_xml_tag_run_bash_parsing_state import CustomXmlTagRunBashParsingState
from autobyteus.agent.streaming.parser.states.xml_tool_parsing_state import XmlToolParsingState
from autobyteus.agent.streaming.parser.states.xml_write_file_tool_parsing_state import XmlWriteFileToolParsingState
from autobyteus.agent.streaming.parser.states.xml_run_bash_tool_parsing_state import XmlRunBashToolParsingState
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


class TestXmlTagInitWriteFileDetection:
    """Tests for <write_file tag detection."""

    def test_write_file_tag_transitions_to_write_file_state(self):
        """<write_file path="..."> triggers transition to CustomXmlTagWriteFileParsingState."""
        ctx = ParserContext()
        ctx.append('<write_file path="/test.py">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, CustomXmlTagWriteFileParsingState)

    def test_write_file_tag_case_insensitive(self):
        """<WRITE_FILE (uppercase) also triggers CustomXmlTagWriteFileParsingState."""
        ctx = ParserContext()
        ctx.append('<WRITE_FILE path="/test.py">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, CustomXmlTagWriteFileParsingState)



class TestXmlTagInitRunBashDetection:
    """Tests for <run_bash> tag detection."""

    def test_run_bash_tag_transitions_to_state(self):
        """<run_bash> triggers transition to CustomXmlTagRunBashParsingState."""
        ctx = ParserContext()
        ctx.append("<run_bash>command</run_bash>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, CustomXmlTagRunBashParsingState)

    def test_run_bash_with_attributes(self):
        """<run_bash description='test'> also triggers CustomXmlTagRunBashParsingState."""
        ctx = ParserContext()
        ctx.append("<run_bash description='test'>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, CustomXmlTagRunBashParsingState)


class TestXmlTagInitToolDetection:
    """Tests for <tool> tag detection."""

    def test_tool_tag_transitions_to_tool_state(self):
        """<tool> triggers transition to XmlToolParsingState when parsing enabled."""
        ctx = ParserContext()  # parse_tool_calls=True by default
        ctx.append("<tool name='test'>")
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlToolParsingState)

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

    def test_partial_write_file_waits_for_more(self):
        """Partial '<write_fil' waits for more characters."""
        ctx = ParserContext()
        ctx.append("<write_fil")  # Incomplete - could be <write_file
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
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

    def test_write_file_tool_detection(self):
        """<tool name="write_file"> triggers transition to XmlWriteFileToolParsingState."""
        ctx = ParserContext()
        ctx.append('<tool name="write_file">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlWriteFileToolParsingState)

    def test_write_file_tool_case_insensitive_name(self):
        """<tool name="WRITE_FILE"> triggers transition to XmlWriteFileToolParsingState."""
        ctx = ParserContext()
        ctx.append('<tool name="WRITE_FILE">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlWriteFileToolParsingState)

    def test_other_tool_transitions_to_generic_tool_state(self):
        """<tool name="other"> triggers transition to XmlToolParsingState."""
        ctx = ParserContext()
        ctx.append('<tool name="other">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlToolParsingState)

    def test_run_bash_tool_detection(self):
        """<tool name="run_bash"> triggers transition to XmlRunBashToolParsingState."""
        ctx = ParserContext()
        ctx.append('<tool name="run_bash">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlRunBashToolParsingState)

    def test_run_bash_tool_case_insensitive_name(self):
        """<tool name="RUN_BASH"> triggers transition to XmlRunBashToolParsingState."""
        ctx = ParserContext()
        ctx.append('<tool name="RUN_BASH">')
        
        state = XmlTagInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlRunBashToolParsingState)
