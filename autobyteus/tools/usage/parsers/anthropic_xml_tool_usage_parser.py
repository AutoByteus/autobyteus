# file: autobyteus/autobyteus/tools/usage/parsers/anthropic_xml_tool_usage_parser.py
from .default_xml_tool_usage_parser import DefaultXmlToolUsageParser

class AnthropicXmlToolUsageParser(DefaultXmlToolUsageParser):
    """
    Parser for Anthropic models. Anthropic uses XML for tool calls,
    so this is an alias for the default XML parser.
    """
    def get_name(self) -> str:
        return "anthropic_xml_tool_usage_parser"
