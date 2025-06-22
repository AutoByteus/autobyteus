# file: autobyteus/autobyteus/tools/usage/registries/xml_example_formatter_registry.py
import logging
from typing import Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters.base_formatter import BaseExampleFormatter
from autobyteus.tools.usage.formatters.default_xml_example_formatter import DefaultXmlExampleFormatter
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class XmlExampleFormatterRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving XML example formatters."""

    def __init__(self):
        self._default_formatter = DefaultXmlExampleFormatter()
        logger.info("XmlExampleFormatterRegistry initialized.")

    def get_formatter(self, provider: Optional[LLMProvider] = None) -> BaseExampleFormatter:
        """
        Retrieves the appropriate XML example formatter.

        Args:
            provider: The LLMProvider enum member. This is currently ignored
                      but is kept for API consistency and future expansion.

        Returns:
            An instance of the DefaultXmlExampleFormatter.
        """
        return self._default_formatter
