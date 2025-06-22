# file: autobyteus/autobyteus/tools/usage/registries/xml_tool_usage_parser_registry.py
import logging
from typing import Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.parsers.base_parser import BaseToolUsageParser
from autobyteus.tools.usage.parsers.default_xml_tool_usage_parser import DefaultXmlToolUsageParser
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class XmlToolUsageParserRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving XML-based tool usage parsers."""

    def __init__(self):
        self._default_parser = DefaultXmlToolUsageParser()
        logger.info("XmlToolUsageParserRegistry initialized.")

    def get_parser(self, provider: Optional[LLMProvider] = None) -> BaseToolUsageParser:
        """
        Retrieves the appropriate XML parser.

        Args:
            provider: The LLMProvider enum member. Currently ignored but kept for API consistency.

        Returns:
            An instance of a class derived from BaseToolUsageParser.
        """
        # For now, there's only one XML format, so always return the default.
        return self._default_parser
