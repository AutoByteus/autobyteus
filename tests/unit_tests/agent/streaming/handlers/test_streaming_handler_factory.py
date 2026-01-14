"""
Unit tests for StreamingResponseHandlerFactory.
"""
from autobyteus.agent.streaming.handlers.streaming_handler_factory import (
    StreamingResponseHandlerFactory,
)
from autobyteus.agent.streaming.handlers.parsing_streaming_response_handler import (
    ParsingStreamingResponseHandler,
)
from autobyteus.agent.streaming.handlers.pass_through_streaming_response_handler import (
    PassThroughStreamingResponseHandler,
)
from autobyteus.agent.streaming.handlers.api_tool_call_streaming_response_handler import (
    ApiToolCallStreamingResponseHandler,
)
from autobyteus.agent.streaming.parser.parser_context import ParserConfig
from autobyteus.llm.providers import LLMProvider


def _factory_kwargs(**overrides):
    base = dict(
        parse_tool_calls=True,
        format_override=None,
        provider=LLMProvider.OPENAI,
        parser_config=ParserConfig(parse_tool_calls=True),
        segment_id_prefix="test:",
        on_segment_event=None,
        on_tool_invocation=None,
        agent_id="agent_test",
    )
    base.update(overrides)
    return base


def test_factory_no_tools_uses_passthrough():
    handler = StreamingResponseHandlerFactory.create(**_factory_kwargs(parse_tool_calls=False))
    assert isinstance(handler, PassThroughStreamingResponseHandler)


def test_factory_api_tool_calls_uses_api_handler():
    handler = StreamingResponseHandlerFactory.create(**_factory_kwargs(format_override="api_tool_call"))
    assert isinstance(handler, ApiToolCallStreamingResponseHandler)


def test_factory_defaults_to_json_for_openai():
    handler = StreamingResponseHandlerFactory.create(**_factory_kwargs(provider=LLMProvider.OPENAI))
    assert isinstance(handler, ParsingStreamingResponseHandler)
    assert handler._parser_name == "json"


def test_factory_defaults_to_xml_for_anthropic():
    handler = StreamingResponseHandlerFactory.create(**_factory_kwargs(provider=LLMProvider.ANTHROPIC))
    assert isinstance(handler, ParsingStreamingResponseHandler)
    assert handler._parser_name == "xml"


def test_factory_respects_format_override_json():
    handler = StreamingResponseHandlerFactory.create(**_factory_kwargs(format_override="json"))
    assert isinstance(handler, ParsingStreamingResponseHandler)
    assert handler._parser_name == "json"


def test_factory_api_tool_call_override_uses_api_handler():
    handler = StreamingResponseHandlerFactory.create(
        **_factory_kwargs(format_override="api_tool_call", provider=LLMProvider.ANTHROPIC)
    )
    assert isinstance(handler, ApiToolCallStreamingResponseHandler)
