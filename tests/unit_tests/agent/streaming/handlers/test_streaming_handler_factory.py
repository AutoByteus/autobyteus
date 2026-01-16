"""
Unit tests for StreamingResponseHandlerFactory.
"""
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.agent.streaming.handlers.streaming_handler_factory import (
    StreamingResponseHandlerFactory,
    StreamingHandlerResult,
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
from autobyteus.llm.providers import LLMProvider


def _factory_kwargs(**overrides):
    """Helper to create factory kwargs with sensible defaults."""
    base = dict(
        tool_names=["test_tool"],
        provider=LLMProvider.OPENAI,
        segment_id_prefix="test:",
        on_segment_event=None,
        on_tool_invocation=None,
        agent_id="agent_test",
    )
    base.update(overrides)
    return base


class TestStreamingHandlerResult:
    """Tests for the StreamingHandlerResult dataclass."""

    def test_result_contains_handler(self):
        """Result should contain the handler."""
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs())
        assert result.handler is not None
        assert isinstance(result, StreamingHandlerResult)


class TestNoToolsMode:
    """Tests for pass-through mode when no tools are configured."""

    def test_no_tools_uses_passthrough(self):
        """Factory should return PassThrough handler when no tools."""
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs(tool_names=[]))
        assert isinstance(result.handler, PassThroughStreamingResponseHandler)
        assert result.tool_schemas is None

    def test_empty_tool_names_uses_passthrough(self):
        """Empty tool_names list should use PassThrough."""
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs(tool_names=[]))
        assert isinstance(result.handler, PassThroughStreamingResponseHandler)


class TestApiToolCallMode:
    """Tests for API tool call mode."""

    def test_api_tool_call_uses_api_handler(self, monkeypatch):
        """Factory should return API handler when format is api_tool_call."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "api_tool_call")
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs())
        assert isinstance(result.handler, ApiToolCallStreamingResponseHandler)

    def test_api_tool_call_builds_schemas(self, monkeypatch):
        """API mode should build tool schemas."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "api_tool_call")
        
        mock_schemas = [{"type": "function", "function": {"name": "test_tool"}}]
        with patch("autobyteus.tools.usage.tool_schema_provider.ToolSchemaProvider") as mock_provider_cls:
            mock_provider_cls.return_value.build_schema.return_value = mock_schemas
            result = StreamingResponseHandlerFactory.create(**_factory_kwargs())
        
        assert result.tool_schemas == mock_schemas
        mock_provider_cls.return_value.build_schema.assert_called_once()

    def test_api_tool_call_without_tools_uses_passthrough(self, monkeypatch):
        """API mode with no tools should still use PassThrough."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "api_tool_call")
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs(tool_names=[]))
        assert isinstance(result.handler, PassThroughStreamingResponseHandler)
        assert result.tool_schemas is None


class TestTextParsingModes:
    """Tests for text parsing modes (XML, JSON, Sentinel)."""

    def test_xml_mode_uses_parsing_handler(self, monkeypatch):
        """XML mode should use parsing handler."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "xml")
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs())
        assert isinstance(result.handler, ParsingStreamingResponseHandler)
        assert result.handler._parser_name == "xml"
        assert result.tool_schemas is None

    def test_json_mode_uses_parsing_handler(self, monkeypatch):
        """JSON mode should use parsing handler."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "json")
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs())
        assert isinstance(result.handler, ParsingStreamingResponseHandler)
        assert result.handler._parser_name == "json"
        assert result.tool_schemas is None

    def test_sentinel_mode_uses_parsing_handler(self, monkeypatch):
        """Sentinel mode should use parsing handler."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "sentinel")
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs())
        assert isinstance(result.handler, ParsingStreamingResponseHandler)
        assert result.handler._parser_name == "sentinel"
        assert result.tool_schemas is None


class TestProviderDefaults:
    """Tests for provider-specific default parser selection."""

    def test_anthropic_defaults_to_xml(self, monkeypatch):
        """Anthropic provider should default to XML parser."""
        # Clear env to use provider-based default
        monkeypatch.delenv("AUTOBYTEUS_STREAM_PARSER", raising=False)
        # Set to some non-api mode to trigger parsing handler
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "default")  # Not a valid mode, falls through
        # Actually we need to NOT set it so it defaults to api_tool_call
        # Let's just test the _resolve_parser_name method directly
        
        parser_name = StreamingResponseHandlerFactory._resolve_parser_name(
            format_override=None,
            provider=LLMProvider.ANTHROPIC,
        )
        assert parser_name == "xml"

    def test_openai_defaults_to_json(self):
        """OpenAI provider should default to JSON parser."""
        parser_name = StreamingResponseHandlerFactory._resolve_parser_name(
            format_override=None,
            provider=LLMProvider.OPENAI,
        )
        assert parser_name == "json"

    def test_gemini_defaults_to_json(self):
        """Gemini provider should default to JSON parser."""
        parser_name = StreamingResponseHandlerFactory._resolve_parser_name(
            format_override=None,
            provider=LLMProvider.GEMINI,
        )
        assert parser_name == "json"


class TestFormatOverride:
    """Tests that format override takes precedence."""

    def test_xml_override_for_openai(self, monkeypatch):
        """XML override should work even for OpenAI provider."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "xml")
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs(provider=LLMProvider.OPENAI))
        assert isinstance(result.handler, ParsingStreamingResponseHandler)
        assert result.handler._parser_name == "xml"

    def test_api_tool_call_override_for_anthropic(self, monkeypatch):
        """API tool call override should work for Anthropic."""
        monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "api_tool_call")
        result = StreamingResponseHandlerFactory.create(**_factory_kwargs(provider=LLMProvider.ANTHROPIC))
        assert isinstance(result.handler, ApiToolCallStreamingResponseHandler)
