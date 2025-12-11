from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from .base_preprocessor import BaseToolInvocationPreprocessor


class ToolInvocationPreprocessorDefinition:
    """
    Lightweight container binding a name to a preprocessor class.
    Mirrors the pattern used by other processor registries.
    """
    def __init__(self, name: str, processor_class: Type['BaseToolInvocationPreprocessor']):
        self.name = name
        self.processor_class: Type['BaseToolInvocationPreprocessor'] = processor_class

