# file: autobyteus/autobyteus/tools/usage/registries/tool_formatting_registry.py
import logging
from typing import Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.singleton import SingletonMeta
from .tool_formatter_pair import ToolFormatterPair
from autobyteus.utils.tool_call_format import resolve_tool_call_format

# Import all necessary formatters
from autobyteus.tools.usage.formatters import (
    DefaultJsonSchemaFormatter, OpenAiJsonSchemaFormatter, AnthropicJsonSchemaFormatter, GeminiJsonSchemaFormatter,
    DefaultJsonExampleFormatter, OpenAiJsonExampleFormatter, AnthropicJsonExampleFormatter, GeminiJsonExampleFormatter,
    DefaultXmlSchemaFormatter, DefaultXmlExampleFormatter,
    # Tool-specific formatters
    WriteFileXmlSchemaFormatter, WriteFileXmlExampleFormatter,
    RunBashXmlSchemaFormatter, RunBashXmlExampleFormatter,
)

logger = logging.getLogger(__name__)

class ToolFormattingRegistry(metaclass=SingletonMeta):
    """
    A consolidated registry that maps an LLMProvider directly to its required
    ToolFormatterPair, which contains both schema and example formatters.
    
    Also supports tool-specific formatter pairs that take priority over provider defaults.
    Priority cascade: tool-specific → provider-specific → default
    """

    def __init__(self):
        # A single, direct mapping from provider to its correct formatter pair.
        self._pairs: Dict[LLMProvider, ToolFormatterPair] = {
            # JSON-based providers
            LLMProvider.OPENAI: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.MISTRAL: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.DEEPSEEK: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.GROK: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.GEMINI: ToolFormatterPair(GeminiJsonSchemaFormatter(), GeminiJsonExampleFormatter()),
            
            # XML-based providers
            LLMProvider.ANTHROPIC: ToolFormatterPair(DefaultXmlSchemaFormatter(), DefaultXmlExampleFormatter()),
        }
        # A default pair for any provider not explicitly listed (defaults to JSON)
        self._default_pair = ToolFormatterPair(DefaultJsonSchemaFormatter(), DefaultJsonExampleFormatter())
        # A specific pair for the XML override
        self._xml_override_pair = ToolFormatterPair(DefaultXmlSchemaFormatter(), DefaultXmlExampleFormatter())
        # Tool-specific formatter pairs (tool_name -> ToolFormatterPair)
        self._tool_pairs: Dict[str, ToolFormatterPair] = {}
        
        # Register tool-specific formatters
        self._register_tool_formatters()
        
        logger.info("ToolFormattingRegistry initialized with direct provider-to-formatter mappings.")

    def _register_tool_formatters(self) -> None:
        """Register built-in tool-specific formatters."""
        # write_file uses shorthand <write_file> syntax
        # write_file uses standard <tool name="write_file"> syntax with custom sentinel instructions
        self._tool_pairs["write_file"] = ToolFormatterPair(
            WriteFileXmlSchemaFormatter(),
            WriteFileXmlExampleFormatter()
        )
        # run_bash uses shorthand <run_bash> syntax
        #self._tool_pairs["run_bash"] = ToolFormatterPair(
        #    RunBashXmlSchemaFormatter(),
        #    RunBashXmlExampleFormatter()
        #)

    def register_tool_formatter(self, tool_name: str, formatter_pair: ToolFormatterPair) -> None:
        """
        Register a tool-specific formatter pair.
        
        Args:
            tool_name: The name of the tool (e.g., 'write_file').
            formatter_pair: The formatter pair to use for this tool.
        """
        self._tool_pairs[tool_name] = formatter_pair
        logger.info(f"Registered tool-specific formatter for '{tool_name}'.")

    def get_formatter_pair_for_tool(
        self, 
        tool_name: str, 
        provider: Optional[LLMProvider]
    ) -> ToolFormatterPair:
        """
        Get the formatter pair for a specific tool with priority cascade.
        
        Priority:
        1. Tool-specific pair (if registered)
        2. Provider-specific pair (if provider known)
        3. Default pair
        
        Args:
            tool_name: The name of the tool.
            provider: The LLM provider.
            
        Returns:
            The appropriate ToolFormatterPair.
        """
        if tool_name in self._tool_pairs:
            logger.debug(f"Using tool-specific formatter for '{tool_name}'.")
            return self._tool_pairs[tool_name]
        return self.get_formatter_pair(provider)

    def get_formatter_pair(self, provider: Optional[LLMProvider]) -> ToolFormatterPair:
        """
        Retrieves the appropriate formatting pair for a given provider, honoring the env format override.

        Args:
            provider: The LLMProvider enum member.

        Returns:
            The corresponding ToolFormatterPair instance.
        """
        format_override = resolve_tool_call_format()
        if format_override == "xml":
            logger.info("Tool format resolved to XML (env override).")
            return self._xml_override_pair
        if format_override == "json":
            logger.info("Tool format resolved to JSON (env override).")
            return self._default_pair
        if format_override in {"sentinel", "native"}:
            logger.info(
                "Tool format '%s' is not supported by formatter registry. "
                "Falling back to JSON formatters.",
                format_override,
            )
            return self._default_pair

        if provider and provider in self._pairs:
            pair = self._pairs[provider]
            logger.info(
                "Tool format resolved by provider '%s' to %s.",
                provider.name,
                "XML" if pair is self._xml_override_pair else "JSON",
            )
            return pair
        
        logger.info(
            "Tool format resolved by default to JSON (provider=%s).",
            provider.name if provider else "Unknown",
        )
        return self._default_pair
