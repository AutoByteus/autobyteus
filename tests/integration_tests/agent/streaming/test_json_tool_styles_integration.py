"""
Integration tests for JSON tool call styles through the streaming handler.
"""
from typing import List, Tuple

import pytest

from autobyteus.agent.streaming import ParsingStreamingResponseHandler
from autobyteus.agent.streaming.parser.parser_context import ParserConfig
from autobyteus.agent.streaming.parser.json_parsing_strategies import get_json_tool_parsing_profile
from autobyteus.llm.providers import LLMProvider


def chunk_text(text: str, chunk_size: int = 7) -> List[str]:
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


@pytest.mark.parametrize(
    "provider, raw_json, expected",
    [
        (
            LLMProvider.OPENAI,
            '{"tool_calls": [{"function": {"name": "weather", "arguments": "{\\"city\\": \\"NYC\\"}"}}]}',
            ("weather", {"city": "NYC"}),
        ),
        (
            LLMProvider.GEMINI,
            '{"name": "search", "args": {"query": "autobyteus"}}',
            ("search", {"query": "autobyteus"}),
        ),
        (
            LLMProvider.KIMI,
            '{"tool": {"function": "write_file", "parameters": {"path": "a.txt"}}}',
            ("write_file", {"path": "a.txt"}),
        ),
    ],
)
def test_json_tool_styles_with_chunking(provider, raw_json, expected):
    profile = get_json_tool_parsing_profile(provider)
    config = ParserConfig(
        parse_tool_calls=True,
        json_tool_patterns=profile.signature_patterns,
        json_tool_parser=profile.parser,
        strategy_order=["json_tool"],
    )
    handler = ParsingStreamingResponseHandler(config=config, parser_name="json")

    for chunk in chunk_text(raw_json, chunk_size=5):
        handler.feed(chunk)

    handler.finalize()

    invocations = handler.get_all_invocations()
    assert len(invocations) == 1
    name, args = expected
    assert invocations[0].name == name
    assert invocations[0].arguments == args
