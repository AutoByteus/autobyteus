# file: autobyteus/autobyteus/tools/usage/registries/xml_schema_formatter_registry.py
import logging
from typing import Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters.base_formatter import BaseSchemaFormatter
from autobyteus.tools.usage.formatters.default_xml_schema_formatter import DefaultXmlSchemaFormatter
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class XmlSchemaFormatterRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving XML schema formatters based on LLM provider."""

    def __init__(self):
        # Currently, there is only one XML format, so all providers map to it.
        # This structure allows for future expansion if providers diverge.
        self._default_formatter = DefaultXmlSchemaFormatter()
        logger.info("XmlSchemaFormatterRegistry initialized.")

    def get_formatter(self, provider: Optional[LLMProvider] = None) -> BaseSchemaFormatter:
        """
        Retrieves the appropriate XML schema formatter.

        Args:
            provider: The LLMProvider enum member. This is currently ignored
                      but is kept for API consistency and future expansion.

        Returns:
            An instance of the DefaultXmlSchemaFormatter.
        """
        # For now, we only have one XML formatter. This always returns it.
        return self._default_formatter
