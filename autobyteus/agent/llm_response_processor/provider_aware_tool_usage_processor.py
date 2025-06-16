# file: autobyteus/autobyteus/agent/llm_response_processor/provider_aware_tool_usage_processor.py
import logging
from typing import TYPE_CHECKING, Optional

from .base_processor import BaseLLMResponseProcessor
from .providers.xml_response_processor_provider import XmlResponseProcessorProvider
from .providers.json_response_processor_provider import JsonResponseProcessorProvider

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import LLMCompleteResponseReceivedEvent
    from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class ProviderAwareToolUsageProcessor(BaseLLMResponseProcessor):
    """
    A "master" tool usage processor that internally delegates to a
    provider-specific processor based on the agent's configuration. This class
    uses lazy initialization for its providers to improve efficiency.
    """
    def __init__(self):
        # Providers are lazy-loaded to avoid unnecessary instantiation.
        self._xml_provider: Optional[XmlResponseProcessorProvider] = None
        self._json_provider: Optional[JsonResponseProcessorProvider] = None
        logger.debug("ProviderAwareToolUsageProcessor initialized.")

    def get_name(self) -> str:
        return "provider_aware_tool_usage"

    async def process_response(self, response: 'CompleteResponse', context: 'AgentContext', triggering_event: 'LLMCompleteResponseReceivedEvent') -> bool:
        """
        Selects the correct underlying processor based on agent configuration
        (XML vs JSON, and the specific LLM provider) and delegates the call.
        """
        # --- Start of Bug Fix ---
        # The provider is on the model, which is on the llm_instance in the context.
        llm_provider = None
        if context.llm_instance and context.llm_instance.model:
            llm_provider = context.llm_instance.model.provider
        else:
            logger.warning(f"Agent '{context.agent_id}': LLM instance or model not available in context. Cannot determine provider for tool response processing.")
        # --- End of Bug Fix ---
        
        # 1. Select and lazy-load the correct format provider (XML or JSON)
        if context.config.use_xml_tool_format:
            if self._xml_provider is None:
                self._xml_provider = XmlResponseProcessorProvider()
            provider = self._xml_provider
            format_name = "XML"
        else:
            if self._json_provider is None:
                self._json_provider = JsonResponseProcessorProvider()
            provider = self._json_provider
            format_name = "JSON"

        # 2. Use the selected provider to get the specific processor for the LLM
        processor = provider.get_processor(llm_provider)

        logger.debug(f"ProviderAwareToolUsageProcessor selected delegate processor '{processor.get_name()}' for format '{format_name}' and LLM provider '{llm_provider.name if llm_provider else 'Unknown'}'.")

        # 3. Delegate the processing to the selected processor
        return await processor.process_response(response, context, triggering_event)
