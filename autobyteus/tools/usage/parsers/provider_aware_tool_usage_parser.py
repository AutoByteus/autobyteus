# file: autobyteus/autobyteus/tools/usage/parsers/provider_aware_tool_usage_parser.py
import logging
from typing import TYPE_CHECKING, List

from .exceptions import ToolUsageParseException

# The import of ToolUsageParserRegistry is deferred to break the circular dependency.
# It is imported at the top level only for static type analysis.
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.llm.utils.response_types import CompleteResponse
    from autobyteus.agent.tool_invocation import ToolInvocation
    from autobyteus.tools.usage.registries.tool_usage_parser_registry import ToolUsageParserRegistry

logger = logging.getLogger(__name__)

class ProviderAwareToolUsageParser:
    """
    A high-level orchestrator that selects and uses the correct tool usage parser
    based on the agent's LLM provider by consulting the central ToolUsageParserRegistry.
    """
    def __init__(self):
        # Local import to break the circular dependency at module load time.
        from autobyteus.tools.usage.registries.tool_usage_parser_registry import ToolUsageParserRegistry
        self._parser_registry: 'ToolUsageParserRegistry' = ToolUsageParserRegistry()
        logger.debug("ProviderAwareToolUsageParser initialized.")

    def parse(self, response: 'CompleteResponse', context: 'AgentContext') -> List['ToolInvocation']:
        """
        Selects the correct underlying parser from the registry, parses the response,
        and returns a list of tool invocations.

        Args:
            response: The CompleteResponse object from the LLM.
            context: The agent's context, used to determine configuration.

        Returns:
            A list of ToolInvocation objects. Returns an empty list if no
            valid tool calls are found.
        """
        llm_provider = None
        if context.llm_instance and context.llm_instance.model:
            llm_provider = context.llm_instance.model.provider
        else:
            logger.warning(f"Agent '{context.agent_id}': LLM instance or model not available. Cannot determine provider for tool response parsing.")
        
        # Retrieve the override flag from the agent's configuration.
        use_xml_tool_format = context.config.use_xml_tool_format

        # Get the correct parser from the registry, passing the override flag.
        parser = self._parser_registry.get_parser(llm_provider, use_xml_tool_format=use_xml_tool_format)
        
        logger.debug(f"ProviderAwareToolUsageParser selected delegate parser '{parser.get_name()}' for LLM provider '{llm_provider.name if llm_provider else 'Unknown'}'.")

        try:
            return parser.parse(response)
        except ToolUsageParseException:
            # Propagate the exception upwards to be handled by the caller.
            raise
