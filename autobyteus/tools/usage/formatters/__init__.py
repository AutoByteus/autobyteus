# file: autobyteus/autobyteus/tools/usage/formatters/__init__.py
"""
This package contains concrete formatter classes that translate a BaseTool's
metadata into a specific provider's format (e.g., OpenAI JSON, Anthropic JSON, XML).
"""
from .base_formatter import BaseSchemaFormatter, BaseExampleFormatter
from .default_xml_schema_formatter import DefaultXmlSchemaFormatter
from .default_json_schema_formatter import DefaultJsonSchemaFormatter
from .openai_json_schema_formatter import OpenAiJsonSchemaFormatter
from .anthropic_json_schema_formatter import AnthropicJsonSchemaFormatter
from .gemini_json_schema_formatter import GeminiJsonSchemaFormatter
from .default_xml_example_formatter import DefaultXmlExampleFormatter
from .default_json_example_formatter import DefaultJsonExampleFormatter
from .openai_json_example_formatter import OpenAiJsonExampleFormatter
from .anthropic_json_example_formatter import AnthropicJsonExampleFormatter
from .gemini_json_example_formatter import GeminiJsonExampleFormatter

# Tool-specific formatters
from .write_file_xml_schema_formatter import WriteFileXmlSchemaFormatter
from .write_file_xml_example_formatter import WriteFileXmlExampleFormatter
from .run_bash_xml_schema_formatter import RunBashXmlSchemaFormatter
from .run_bash_xml_example_formatter import RunBashXmlExampleFormatter

__all__ = [
    "BaseSchemaFormatter",
    "BaseExampleFormatter",
    "DefaultXmlSchemaFormatter",
    "DefaultJsonSchemaFormatter",
    "OpenAiJsonSchemaFormatter",
    "AnthropicJsonSchemaFormatter",
    "GeminiJsonSchemaFormatter",
    "DefaultXmlExampleFormatter",
    "DefaultJsonExampleFormatter",
    "OpenAiJsonExampleFormatter",
    "AnthropicJsonExampleFormatter",
    "GeminiJsonExampleFormatter",
    # Tool-specific formatters
    "WriteFileXmlSchemaFormatter",
    "WriteFileXmlExampleFormatter",
    "RunBashXmlSchemaFormatter",
    "RunBashXmlExampleFormatter",
]

