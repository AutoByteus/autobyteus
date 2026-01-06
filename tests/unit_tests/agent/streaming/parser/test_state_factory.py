"""
Unit tests for the StateFactory.

Updated to match the new unified architecture where all content states
receive opening_tag in their constructor.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.state_factory import StateFactory
from autobyteus.agent.streaming.parser.states.base_state import BaseState


class TestStateFactory:
    """Tests for StateFactory."""

    def test_create_text_state(self):
        """Factory creates TextState."""
        ctx = ParserContext()
        state = StateFactory.text_state(ctx)
        assert isinstance(state, BaseState)
        assert state.__class__.__name__ == "TextState"

    def test_create_xml_tag_init_state(self):
        """Factory creates XmlTagInitializationState."""
        ctx = ParserContext()
        ctx.append("<test")  # Need content
        state = StateFactory.xml_tag_init_state(ctx)
        assert state.__class__.__name__ == "XmlTagInitializationState"

    def test_create_write_file_parsing_state(self):
        """Factory creates CustomXmlTagWriteFileParsingState with opening_tag."""
        ctx = ParserContext()
        ctx.append("content</write_file>")
        state = StateFactory.write_file_parsing_state(ctx, "<write_file path='/test.py'>")
        assert state.__class__.__name__ == "CustomXmlTagWriteFileParsingState"

    def test_create_run_bash_parsing_state(self):
        """Factory creates CustomXmlTagRunBashParsingState."""
        ctx = ParserContext()
        state = StateFactory.run_bash_parsing_state(ctx, "<run_bash>")
        assert state.__class__.__name__ == "CustomXmlTagRunBashParsingState"

    def test_create_xml_tool_parsing_state(self):
        """Factory creates XmlToolParsingState."""
        ctx = ParserContext()
        ctx.append("content</tool>")
        state = StateFactory.xml_tool_parsing_state(ctx, "<tool name='test'>")
        assert state.__class__.__name__ == "XmlToolParsingState"

    def test_create_json_init_state(self):
        """Factory creates JsonInitializationState."""
        ctx = ParserContext()
        ctx.append('{"name": "test"}')
        state = StateFactory.json_init_state(ctx)
        assert state.__class__.__name__ == "JsonInitializationState"

    def test_create_json_tool_parsing_state(self):
        """Factory creates JsonToolParsingState."""
        ctx = ParserContext()
        ctx.append('{"name": "test", "arguments": {}}')
        state = StateFactory.json_tool_parsing_state(ctx, '{"name"')
        assert state.__class__.__name__ == "JsonToolParsingState"

    def test_all_states_have_run_method(self):
        """All created states have required methods."""
        ctx = ParserContext()
        ctx.append("content</test>")
        
        states = [
            StateFactory.text_state(ctx),
            StateFactory.write_file_parsing_state(ctx, "<write_file path='/test'>"),
            StateFactory.run_bash_parsing_state(ctx, "<run_bash>"),
        ]
        
        for state in states:
            assert hasattr(state, 'run')
            assert hasattr(state, 'finalize')

