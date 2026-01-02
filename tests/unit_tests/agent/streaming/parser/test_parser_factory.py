"""
Unit tests for streaming parser factory selection.
"""
import pytest

from autobyteus.agent.streaming.parser.parser_factory import (
    ENV_PARSER_NAME,
    create_streaming_parser,
    resolve_parser_name,
)
from autobyteus.agent.streaming.parser.parser_context import ParserConfig
from autobyteus.agent.streaming.parser.streaming_parser import StreamingParser


def test_resolve_parser_name_defaults_to_fsm(monkeypatch):
    monkeypatch.delenv(ENV_PARSER_NAME, raising=False)
    assert resolve_parser_name() == "fsm"


def test_resolve_parser_name_env_override(monkeypatch):
    monkeypatch.setenv(ENV_PARSER_NAME, "native")
    assert resolve_parser_name() == "native"


def test_create_fsm_parser():
    parser = create_streaming_parser(parser_name="fsm")
    assert isinstance(parser, StreamingParser)


def test_create_native_parser_disables_tool_parsing():
    config = ParserConfig(parse_tool_calls=True, use_xml_tool_format=True)
    parser = create_streaming_parser(config=config, parser_name="native")
    assert parser.config.parse_tool_calls is False


def test_create_sentinel_parser():
    parser = create_streaming_parser(parser_name="sentinel")
    assert isinstance(parser, StreamingParser)


def test_unknown_parser_raises():
    with pytest.raises(ValueError):
        create_streaming_parser(parser_name="unknown")
