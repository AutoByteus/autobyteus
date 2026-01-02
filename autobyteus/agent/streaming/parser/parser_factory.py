"""
Parser factory and strategy selection for streaming parsers.

Selects a parser implementation based on configuration or environment.
"""
from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional, Protocol

from .events import SegmentEvent
from .parser_context import ParserConfig
from .streaming_parser import StreamingParser


class StreamingParserProtocol(Protocol):
    """Protocol for streaming parsers used by the response handler."""

    @property
    def config(self) -> ParserConfig:
        ...

    def feed(self, chunk: str) -> List[SegmentEvent]:
        ...

    def finalize(self) -> List[SegmentEvent]:
        ...


ENV_PARSER_NAME = "AUTOBYTEUS_STREAM_PARSER"
DEFAULT_PARSER_NAME = "xml"


def _clone_config(
    config: Optional[ParserConfig],
    *,
    parse_tool_calls: Optional[bool] = None,
    json_tool_patterns: Optional[List[str]] = None,
    strategy_order: Optional[List[str]] = None,
) -> ParserConfig:
    base = config or ParserConfig()
    return ParserConfig(
        parse_tool_calls=base.parse_tool_calls if parse_tool_calls is None else parse_tool_calls,
        json_tool_patterns=(
            base.json_tool_patterns.copy()
            if json_tool_patterns is None
            else json_tool_patterns
        ),
        strategy_order=(
            base.strategy_order.copy()
            if strategy_order is None
            else strategy_order
        ),
    )


def _build_xml(config: Optional[ParserConfig]) -> StreamingParserProtocol:
    xml_config = _clone_config(
        config,
        parse_tool_calls=True,
        strategy_order=["xml_tag"],
    )
    return StreamingParser(config=xml_config)


def _build_json(config: Optional[ParserConfig]) -> StreamingParserProtocol:
    json_config = _clone_config(
        config,
        parse_tool_calls=True,
        strategy_order=["json_tool"],
    )
    return StreamingParser(config=json_config)


def _build_native(config: Optional[ParserConfig]) -> StreamingParserProtocol:
    # Native tool calls handled elsewhere; keep tag parsing but disable tool parsing.
    native_config = _clone_config(config, parse_tool_calls=False)
    return StreamingParser(config=native_config)


def _build_sentinel(config: Optional[ParserConfig]) -> StreamingParserProtocol:
    sentinel_config = _clone_config(
        config,
        strategy_order=["sentinel"],
        parse_tool_calls=True,
    )
    return StreamingParser(config=sentinel_config)


PARSER_REGISTRY: Dict[str, Callable[[Optional[ParserConfig]], StreamingParserProtocol]] = {
    "xml": _build_xml,
    "json": _build_json,
    "native": _build_native,
    "sentinel": _build_sentinel,
}


def resolve_parser_name(explicit_name: Optional[str] = None) -> str:
    """Resolve parser name from explicit value or environment."""
    name = explicit_name or os.getenv(ENV_PARSER_NAME, DEFAULT_PARSER_NAME)
    return name.strip().lower()


def create_streaming_parser(
    config: Optional[ParserConfig] = None,
    *,
    parser_name: Optional[str] = None,
) -> StreamingParserProtocol:
    """Create a streaming parser based on configuration or environment."""
    name = resolve_parser_name(parser_name)
    builder = PARSER_REGISTRY.get(name)
    if builder is None:
        raise ValueError(
            f"Unknown parser strategy '{name}'. "
            f"Supported: {', '.join(sorted(PARSER_REGISTRY))}."
        )
    return builder(config)
