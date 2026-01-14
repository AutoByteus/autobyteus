# file: autobyteus/autobyteus/agent/streaming/streaming_handler_factory.py
"""
Factory for selecting the appropriate StreamingResponseHandler implementation.
"""
from __future__ import annotations

import logging
from typing import Optional, Callable

from autobyteus.agent.tool_invocation import ToolInvocation
from .streaming_response_handler import StreamingResponseHandler
from .parsing_streaming_response_handler import ParsingStreamingResponseHandler
from .pass_through_streaming_response_handler import PassThroughStreamingResponseHandler
from .api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from ..parser.parser_context import ParserConfig
from ..segments.segment_events import SegmentEvent
from autobyteus.llm.providers import LLMProvider

logger = logging.getLogger(__name__)


class StreamingResponseHandlerFactory:
    """Factory for building streaming response handlers based on config/state."""

    @staticmethod
    def create(
        *,
        parse_tool_calls: bool,
        format_override: Optional[str],
        provider: Optional[LLMProvider],
        parser_config: ParserConfig,
        segment_id_prefix: str,
        on_segment_event: Optional[Callable[[SegmentEvent], None]] = None,
        on_tool_invocation: Optional[Callable[[ToolInvocation], None]] = None,
        agent_id: Optional[str] = None,
    ) -> StreamingResponseHandler:
        override = format_override.strip().lower() if format_override else None
        if not parse_tool_calls:
            logger.debug(
                "Agent '%s': No tools enabled - Configuring PassThroughStreamingResponseHandler",
                agent_id or "unknown",
            )
            return PassThroughStreamingResponseHandler(
                on_segment_event=on_segment_event,
                on_tool_invocation=on_tool_invocation,
                segment_id_prefix=segment_id_prefix,
            )

        if override in {"api_tool_call", "native"}:
            logger.debug(
                "Agent '%s': Configuring ApiToolCallStreamingResponseHandler",
                agent_id or "unknown",
            )
            return ApiToolCallStreamingResponseHandler(
                on_segment_event=on_segment_event,
                on_tool_invocation=on_tool_invocation,
                segment_id_prefix=segment_id_prefix,
            )

        parser_name = StreamingResponseHandlerFactory._resolve_parser_name(
            format_override=override,
            provider=provider,
            agent_id=agent_id,
        )
        logger.debug(
            "Agent '%s': Tools enabled - Configuring ParsingStreamingResponseHandler with %s parser",
            agent_id or "unknown",
            parser_name,
        )
        return ParsingStreamingResponseHandler(
            on_segment_event=on_segment_event,
            on_tool_invocation=on_tool_invocation,
            config=parser_config,
            parser_name=parser_name,
        )

    @staticmethod
    def _resolve_parser_name(
        *,
        format_override: Optional[str],
        provider: Optional[LLMProvider],
        agent_id: Optional[str] = None,
    ) -> str:
        if format_override in {"xml", "json", "sentinel"}:
            return format_override

        return "xml" if provider == LLMProvider.ANTHROPIC else "json"
