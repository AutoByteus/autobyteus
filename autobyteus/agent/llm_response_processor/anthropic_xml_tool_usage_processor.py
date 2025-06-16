# file: autobyteus/autobyteus/agent/llm_response_processor/anthropic_xml_tool_usage_processor.py
from .default_xml_tool_usage_processor import DefaultXmlToolUsageProcessor

class AnthropicXmlToolUsageProcessor(DefaultXmlToolUsageProcessor):
    """
    Processor for Anthropic models. Anthropic uses XML for tool calls,
    so this is an alias for the default XML processor.
    """
    def get_name(self) -> str:
        return "anthropic_xml_tool_usage"
