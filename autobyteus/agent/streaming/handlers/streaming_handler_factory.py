# file: autobyteus/autobyteus/agent/streaming/handlers/streaming_handler_factory.py
"""
Factory for selecting the appropriate StreamingResponseHandler implementation.

This factory encapsulates all configuration logic including:
- Format/mode resolution from environment
- ParserConfig construction for text parsing modes
- JSON profile selection for provider-aware parsing
- Tool schema building for API tool call mode
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.tool_call_format import resolve_tool_call_format

from .streaming_response_handler import StreamingResponseHandler
from .parsing_streaming_response_handler import ParsingStreamingResponseHandler
from .pass_through_streaming_response_handler import PassThroughStreamingResponseHandler
from .api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from ..parser.parser_context import ParserConfig
from ..parser.json_parsing_strategies.registry import get_json_tool_parsing_profile
from ..segments.segment_events import SegmentEvent

logger = logging.getLogger(__name__)


@dataclass
class StreamingHandlerResult:
    """
    Result of creating a streaming handler.
    
    Attributes:
        handler: The configured streaming response handler.
        tool_schemas: Pre-built tool schemas for API mode (None for other modes).
    """
    handler: StreamingResponseHandler
    tool_schemas: Optional[List[Dict]] = None


class StreamingResponseHandlerFactory:
    """Factory for building streaming response handlers based on minimal inputs."""

    @staticmethod
    def create(
        *,
        tool_names: List[str],
        provider: Optional[LLMProvider],
        segment_id_prefix: Optional[str] = None,
        on_segment_event: Optional[Callable[[SegmentEvent], None]] = None,
        on_tool_invocation: Optional[Callable[[ToolInvocation], None]] = None,
        agent_id: Optional[str] = None,
    ) -> StreamingHandlerResult:
        """
        Create a streaming response handler with all necessary configuration.
        
        Args:
            tool_names: List of tool names the agent has access to.
            provider: The LLM provider being used (for provider-specific parsing).
            segment_id_prefix: Optional prefix for segment IDs.
            on_segment_event: Callback for UI streaming events.
            on_tool_invocation: Callback when a tool invocation is created.
            agent_id: Agent identifier for logging.
            
        Returns:
            StreamingHandlerResult containing the handler and optional tool schemas.
        """
        # Resolve format from environment
        format_override = resolve_tool_call_format()
        parse_tool_calls = bool(tool_names)
        
        # Generate segment ID prefix if not provided
        if segment_id_prefix is None:
            segment_id_prefix = f"turn_{uuid.uuid4().hex}:"
        
        # No tools → PassThrough handler
        if not parse_tool_calls:
            logger.debug(
                "Agent '%s': No tools enabled - using PassThroughStreamingResponseHandler",
                agent_id or "unknown",
            )
            return StreamingHandlerResult(
                handler=PassThroughStreamingResponseHandler(
                    on_segment_event=on_segment_event,
                    on_tool_invocation=on_tool_invocation,
                    segment_id_prefix=segment_id_prefix,
                ),
                tool_schemas=None,
            )
        
        # API tool call mode → ApiToolCall handler + build schemas
        if format_override == "api_tool_call":
            logger.debug(
                "Agent '%s': Using ApiToolCallStreamingResponseHandler",
                agent_id or "unknown",
            )
            # Build tool schemas for API mode
            tool_schemas = StreamingResponseHandlerFactory._build_tool_schemas(
                tool_names=tool_names,
                provider=provider,
            )
            return StreamingHandlerResult(
                handler=ApiToolCallStreamingResponseHandler(
                    on_segment_event=on_segment_event,
                    on_tool_invocation=on_tool_invocation,
                    segment_id_prefix=segment_id_prefix,
                ),
                tool_schemas=tool_schemas,
            )
        
        # Text parsing mode (XML/JSON/Sentinel) → Parsing handler
        parser_name = StreamingResponseHandlerFactory._resolve_parser_name(
            format_override=format_override,
            provider=provider,
        )
        
        # Build ParserConfig with provider-aware JSON profile
        json_profile = get_json_tool_parsing_profile(provider)
        parser_config = ParserConfig(
            parse_tool_calls=parse_tool_calls,
            json_tool_patterns=json_profile.signature_patterns,
            json_tool_parser=json_profile.parser,
            segment_id_prefix=segment_id_prefix,
        )
        
        logger.debug(
            "Agent '%s': Using ParsingStreamingResponseHandler with %s parser",
            agent_id or "unknown",
            parser_name,
        )
        return StreamingHandlerResult(
            handler=ParsingStreamingResponseHandler(
                on_segment_event=on_segment_event,
                on_tool_invocation=on_tool_invocation,
                config=parser_config,
                parser_name=parser_name,
            ),
            tool_schemas=None,
        )

    @staticmethod
    def _resolve_parser_name(
        *,
        format_override: Optional[str],
        provider: Optional[LLMProvider],
    ) -> str:
        """Resolve which parser to use based on format and provider."""
        if format_override in {"xml", "json", "sentinel"}:
            return format_override
        # Default: XML for Anthropic, JSON for others
        return "xml" if provider == LLMProvider.ANTHROPIC else "json"

    @staticmethod
    def _build_tool_schemas(
        tool_names: List[str],
        provider: Optional[LLMProvider],
    ) -> Optional[List[Dict]]:
        """Build tool schemas for API tool call mode."""
        if not tool_names:
            return None
        
        # Import here to avoid circular dependency
        from autobyteus.tools.usage.tool_schema_provider import ToolSchemaProvider
        
        schemas = ToolSchemaProvider().build_schema(tool_names, provider)
        if schemas:
            logger.debug(
                "Built %d tool schemas for API tool calls (provider: %s)",
                len(schemas),
                provider,
            )
        return schemas if schemas else None
