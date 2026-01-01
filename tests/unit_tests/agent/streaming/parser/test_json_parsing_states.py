"""
Unit tests for JSON parsing states.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext, ParserConfig
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.json_initialization_state import (
    JsonInitializationState,
    JsonToolSignatureChecker
)
from autobyteus.agent.streaming.parser.states.json_tool_parsing_state import JsonToolParsingState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestJsonSignatureChecker:
    """Tests for JsonToolSignatureChecker."""

    def test_match_name_pattern(self):
        """{"name": pattern matches."""
        checker = JsonToolSignatureChecker()
        assert checker.check_signature('{"name"') == 'match'

    def test_match_tool_pattern(self):
        """{"tool": pattern matches."""
        checker = JsonToolSignatureChecker()
        assert checker.check_signature('{"tool"') == 'match'

    def test_match_array_pattern(self):
        """[{"name": pattern matches."""
        checker = JsonToolSignatureChecker()
        assert checker.check_signature('[{"name"') == 'match'

    def test_partial_signature(self):
        """Partial signature returns partial."""
        checker = JsonToolSignatureChecker()
        assert checker.check_signature('{') == 'partial'
        assert checker.check_signature('{"') == 'partial'
        assert checker.check_signature('{"n') == 'partial'

    def test_no_match(self):
        """Non-tool JSON returns no_match."""
        checker = JsonToolSignatureChecker()
        assert checker.check_signature('{"data"') == 'no_match'
        assert checker.check_signature('{"items"') == 'no_match'

    def test_custom_patterns(self):
        """Custom patterns can be used."""
        custom = ['{"action"', '{"command"']
        checker = JsonToolSignatureChecker(custom)
        
        assert checker.check_signature('{"action"') == 'match'
        assert checker.check_signature('{"command"') == 'match'
        assert checker.check_signature('{"name"') == 'no_match'  # Not in custom


class TestJsonInitializationState:
    """Tests for JsonInitializationState."""

    def test_tool_signature_transitions(self):
        """Tool signature triggers transition to JsonToolParsingState."""
        config = ParserConfig(parse_tool_calls=True, use_xml_tool_format=False)
        ctx = ParserContext(config)
        ctx.append('{"name": "test", "arguments": {}}more')
        
        state = JsonInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should transition to JsonToolParsingState
        assert isinstance(ctx.current_state, JsonToolParsingState)

    def test_non_tool_becomes_text(self):
        """Non-tool JSON becomes text."""
        config = ParserConfig(parse_tool_calls=True, use_xml_tool_format=False)
        ctx = ParserContext(config)
        ctx.append('{"data": [1,2,3]}more')
        
        state = JsonInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should revert to TextState
        assert isinstance(ctx.current_state, TextState)
        
        # Buffer should be emitted as text
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        assert len(content_events) > 0

    def test_tool_disabled_becomes_text(self):
        """Tool signature becomes text when parsing disabled."""
        config = ParserConfig(parse_tool_calls=False, use_xml_tool_format=False)
        ctx = ParserContext(config)
        ctx.append('{"name": "test"}more')
        
        state = JsonInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should revert to TextState even with tool signature
        assert isinstance(ctx.current_state, TextState)

    def test_finalize_emits_buffer(self):
        """Finalize emits buffered content as text."""
        config = ParserConfig(parse_tool_calls=True, use_xml_tool_format=False)
        ctx = ParserContext(config)
        ctx.append('{"na')  # Partial signature
        
        state = JsonInitializationState(ctx)
        ctx.current_state = state
        state.run()
        
        state.finalize()
        
        events = ctx.get_and_clear_events()
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        assert any('{"na' in e.payload.get("delta", "") for e in content_events)


class TestJsonToolParsingState:
    """Tests for JsonToolParsingState."""

    def test_simple_tool_call(self):
        """Parse simple JSON tool call."""
        ctx = ParserContext()
        signature = '{"name"'
        ctx.append('{"name": "weather", "arguments": {"city": "NYC"}}after')
        
        state = JsonToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Should have tool call segment
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.TOOL_CALL

    def test_nested_json(self):
        """Parse tool call with nested JSON."""
        ctx = ParserContext()
        signature = '{"name"'
        ctx.append('{"name": "api", "arguments": {"data": {"nested": true}}}after')
        
        state = JsonToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_array_format(self):
        """Parse array format tool calls."""
        ctx = ParserContext()
        signature = '[{"name"'
        ctx.append('[{"name": "tool1", "arguments": {}}]after')
        
        state = JsonToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1

    def test_string_with_braces(self):
        """Braces inside strings are handled correctly."""
        ctx = ParserContext()
        signature = '{"name"'
        ctx.append('{"name": "test", "arguments": {"code": "if (a) { b }"}}after')
        
        state = JsonToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
        assert isinstance(ctx.current_state, TextState)

    def test_finalize_incomplete_json(self):
        """Finalize handles incomplete JSON."""
        ctx = ParserContext()
        signature = '{"name"'
        ctx.append('{"name": "test", "arguments": {')
        
        state = JsonToolParsingState(ctx, signature)
        ctx.current_state = state
        state.run()
        
        state.finalize()
        
        events = ctx.get_and_clear_events()
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) >= 1
