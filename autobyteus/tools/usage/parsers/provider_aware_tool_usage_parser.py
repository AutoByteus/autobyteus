# file: autobyteus/autobyteus/tools/usage/parsers/provider_aware_tool_usage_parser.py
import logging
from typing import TYPE_CHECKING, Optional, List

from .exceptions import ToolUsageParseException

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.llm.utils.response_types import CompleteResponse
    from autobyteus.agent.tool_invocation import ToolInvocation
    from autobyteus.tools.usage.providers import XmlToolUsageParserProvider, JsonToolUsageParserProvider

logger = logging.getLogger(__name__)

class ProviderAwareToolUsageParser:
    """
    A high-level orchestrator that selects and uses the correct tool usage parser
    (e.g., for XML, OpenAI JSON, Gemini JSON) based on the agent's configuration.
    
    This class encapsulates the logic for choosing a parser, making it easy for
    other components to simply request a parse without knowing the underlying details.
    """
    def __init__(self):
        self._xml_parser_provider: Optional['XmlToolUsageParserProvider'] = None
        self._json_parser_provider: Optional['JsonToolUsageParserProvider'] = None
        logger.debug("ProviderAwareToolUsageParser initialized.")

    def parse(self, response: 'CompleteResponse', context: 'AgentContext') -> List['ToolInvocation']:
        """
        Selects the correct underlying parser, parses the response, and returns
        a list of tool invocations.

        Args:
            response: The CompleteResponse object from the LLM.
            context: The agent's context, used to determine configuration.

        Returns:
            A list of ToolInvocation objects. Returns an empty list if no
            valid tool calls are found.
        """
        from autobyteus.tools.usage.providers import XmlToolUsageParserProvider, JsonToolUsageParserProvider

        llm_provider = None
        if context.llm_instance and context.llm_instance.model:
            llm_provider = context.llm_instance.model.provider
        else:
            logger.warning(f"Agent '{context.agent_id}': LLM instance or model not available. Cannot determine provider for tool response parsing.")
        
        if context.config.use_xml_tool_format:
            if self._xml_parser_provider is None:
                self._xml_parser_provider = XmlToolUsageParserProvider()
            parser_provider = self._xml_parser_provider
            format_name = "XML"
        else:
            if self._json_parser_provider is None:
                self._json_parser_provider = JsonToolUsageParserProvider()
            parser_provider = self._json_parser_provider
            format_name = "JSON"

        parser = parser_provider.provide(llm_provider)
        logger.debug(f"ProviderAwareToolUsageParser selected delegate parser '{parser.get_name()}' for format '{format_name}' and LLM provider '{llm_provider.name if llm_provider else 'Unknown'}'.")

        try:
            return parser.parse(response)
        except ToolUsageParseException:
            # Propagate the exception upwards to be handled by the caller.
            raise
