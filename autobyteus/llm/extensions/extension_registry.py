
from typing import List, Type, TypeVar, Generic, Optional
from autobyteus.llm.extensions.base_extension import LLMExtension

T = TypeVar('T', bound=LLMExtension)

class ExtensionRegistry:
    """
    Manages LLM extensions and provides attribute-style access to them.
    """
    def __init__(self):
        self._extensions: List[LLMExtension] = []

    def register(self, extension: LLMExtension) -> None:
        """Register a new extension."""
        if not any(isinstance(ext, type(extension)) for ext in self._extensions):
            self._extensions.append(extension)

    def unregister(self, extension: LLMExtension) -> None:
        """Unregister an existing extension."""
        if extension in self._extensions:
            self._extensions.remove(extension)

    def get(self, extension_class: Type[T]) -> Optional[T]:
        """Get a registered extension by its class."""
        for ext in self._extensions:
            if isinstance(ext, extension_class):
                return ext
        return None

    def get_all(self) -> List[LLMExtension]:
        """Get all registered extensions."""
        return self._extensions.copy()

    def clear(self) -> None:
        """Remove all extensions."""
        self._extensions.clear()
