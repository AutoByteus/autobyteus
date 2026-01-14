# file: autobyteus/autobyteus/tools/usage/tool_schema_provider.py
"""
Provider-aware tool schema builder for API tool calls.
"""
from __future__ import annotations

import logging
from typing import Iterable, List, Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.usage.formatters.anthropic_json_schema_formatter import AnthropicJsonSchemaFormatter
from autobyteus.tools.usage.formatters.gemini_json_schema_formatter import GeminiJsonSchemaFormatter
from autobyteus.tools.usage.formatters.openai_json_schema_formatter import OpenAiJsonSchemaFormatter
from autobyteus.tools.registry.tool_definition import ToolDefinition

logger = logging.getLogger(__name__)


class ToolSchemaProvider:
    """Builds API tool schemas for a provider."""

    def __init__(self, registry=default_tool_registry):
        self._registry = registry

    def build_schema(
        self,
        tool_names: Iterable[str],
        provider: Optional[LLMProvider],
    ) -> List[Dict]:
        tool_definitions: List[ToolDefinition] = []
        for name in tool_names:
            tool_def = self._registry.get_tool_definition(name)
            if tool_def:
                tool_definitions.append(tool_def)
            else:
                logger.warning("Tool '%s' not found in registry.", name)

        if not tool_definitions:
            return []

        formatter = self._select_formatter(provider)
        return [formatter.provide(td) for td in tool_definitions]

    @staticmethod
    def _select_formatter(provider: Optional[LLMProvider]):
        if provider == LLMProvider.ANTHROPIC:
            return AnthropicJsonSchemaFormatter()
        if provider == LLMProvider.GEMINI:
            return GeminiJsonSchemaFormatter()
        return OpenAiJsonSchemaFormatter()
