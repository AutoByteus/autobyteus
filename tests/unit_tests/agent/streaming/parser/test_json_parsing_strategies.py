"""Unit tests for JSON tool parsing strategies."""
from autobyteus.agent.streaming.parser.json_parsing_strategies import (
    OpenAiJsonToolParsingStrategy,
    GeminiJsonToolParsingStrategy,
    DefaultJsonToolParsingStrategy,
    get_json_tool_parsing_profile,
)
from autobyteus.llm.providers import LLMProvider


def test_openai_parser_tool_wrapper():
    parser = OpenAiJsonToolParsingStrategy()
    raw = '{"tool": {"function": {"name": "weather", "arguments": {"city": "NYC"}}}}'
    parsed = parser.parse(raw)
    assert parsed == [{"name": "weather", "arguments": {"city": "NYC"}}]


def test_openai_parser_tool_calls_wrapper():
    parser = OpenAiJsonToolParsingStrategy()
    raw = '{"tool_calls": [{"function": {"name": "weather", "arguments": "{\\"city\\": \\"NYC\\"}"}}]}'
    parsed = parser.parse(raw)
    assert parsed == [{"name": "weather", "arguments": {"city": "NYC"}}]


def test_gemini_parser_args():
    parser = GeminiJsonToolParsingStrategy()
    raw = '{"name": "search", "args": {"query": "autobyteus"}}'
    parsed = parser.parse(raw)
    assert parsed == [{"name": "search", "arguments": {"query": "autobyteus"}}]


def test_default_parser_parameters():
    parser = DefaultJsonToolParsingStrategy()
    raw = '{"tool": {"function": "write_file", "parameters": {"path": "a.txt"}}}'
    parsed = parser.parse(raw)
    assert parsed == [{"name": "write_file", "arguments": {"path": "a.txt"}}]


def test_registry_profiles():
    gemini_profile = get_json_tool_parsing_profile(LLMProvider.GEMINI)
    assert isinstance(gemini_profile.parser, GeminiJsonToolParsingStrategy)

    openai_profile = get_json_tool_parsing_profile(LLMProvider.OPENAI)
    assert isinstance(openai_profile.parser, OpenAiJsonToolParsingStrategy)

    default_profile = get_json_tool_parsing_profile(LLMProvider.KIMI)
    assert isinstance(default_profile.parser, DefaultJsonToolParsingStrategy)
