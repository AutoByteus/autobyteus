import logging
from typing import TYPE_CHECKING, Type, Optional, List, Iterator
from dataclasses import dataclass

from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """A simple data structure for essential model information."""
    name: str
    canonical_name: str

@dataclass
class ProviderModelGroup:
    """A data structure to group models by their provider."""
    provider: str
    models: List[ModelInfo]

class LLMModelMeta(type):
    """
    Metaclass for LLMModel to make it iterable and support item access like Enums.
    It also ensures that LLMFactory is initialized before iteration or item access.
    """
    def __iter__(cls) -> Iterator['LLMModel']:
        """
        Allows iteration over LLMModel instances (e.g., `for model in LLMModel:`).
        Ensures that the LLMFactory has initialized and registered all models.
        """
        # Import LLMFactory locally to prevent circular import issues at module load time.
        from autobyteus.llm.llm_factory import LLMFactory
        LLMFactory.ensure_initialized()

        for models in LLMFactory._models_by_provider.values():
            yield from models

    def __getitem__(cls, name_or_value: str) -> 'LLMModel':
        """
        Allows dictionary-like access to LLMModel instances by name (e.g., 'gpt-4o')
        or by value (e.g., 'gpt-4o').
        Search is performed by name first, then by value.
        """
        # Import LLMFactory locally to prevent circular import issues at module load time.
        from autobyteus.llm.llm_factory import LLMFactory
        LLMFactory.ensure_initialized()

        # 1. Try to find by name first
        for model in cls:
            if model.name == name_or_value:
                return model
        
        # 2. If not found by name, iterate and find by value
        for model in cls:
            if model.value == name_or_value:
                return model
        
        # 3. If not found by name or value, raise KeyError
        available_models = [m.name for m in cls] 
        raise KeyError(f"Model '{name_or_value}' not found. Available models are: {available_models}")

    def __len__(cls) -> int:
        """
        Allows getting the number of registered models (e.g., `len(LLMModel)`).
        """
        # Import LLMFactory locally.
        from autobyteus.llm.llm_factory import LLMFactory
        LLMFactory.ensure_initialized()
        
        count = 0
        for models in LLMFactory._models_by_provider.values():
            count += len(models)
        return count

class LLMModel(metaclass=LLMModelMeta):
    """
    Represents a single model's metadata:
      - name (str): A human-readable label, e.g. "gpt-4o"
      - value (str): A unique identifier used in code or APIs, e.g. "gpt-4o"
      - canonical_name (str): A shorter, standardized reference name for prompts, e.g. "gpt-4o" or "claude-3.7"
      - provider (LLMProvider): The provider enum 
      - llm_class (Type[BaseLLM]): Which Python class to instantiate 
      - default_config (LLMConfig): Default configuration (token limit, etc.)

    Each model also exposes a create_llm() method to instantiate the underlying class.
    Supports Enum-like access via `LLMModel['MODEL_NAME']` and iteration `for model in LLMModel:`.
    """

    def __init__(
        self,
        name: str,
        value: str,
        provider: LLMProvider,
        llm_class: Type["BaseLLM"],
        canonical_name: str,
        default_config: Optional[LLMConfig] = None
    ):
        self._name = name
        self._value = value
        self._canonical_name = canonical_name
        self.provider = provider
        self.llm_class = llm_class
        self.default_config = default_config if default_config else LLMConfig()

    @property
    def name(self) -> str:
        """
        A friendly or descriptive name for this model (could appear in UI).
        This is the key used for `LLMModel['MODEL_NAME']` access.
        Example: "gpt-4o"
        """
        return self._name

    @property
    def value(self) -> str:
        """
        The underlying unique identifier for this model (e.g. an API model string).
        Example: "gpt-4o"
        """
        return self._value

    @property
    def canonical_name(self) -> str:
        """
        A standardized, shorter reference name for this model.
        Useful for prompt engineering and cross-referencing similar models.
        Example: "gpt-4o"
        """
        return self._canonical_name

    def create_llm(self, llm_config: Optional[LLMConfig] = None) -> "BaseLLM":
        """
        Instantiate the LLM class for this model, applying
        an optional llm_config override if supplied.

        Args:
            llm_config (Optional[LLMConfig]): Specific configuration to use.
                                              If None, model's default_config is used.
        
        Returns:
            BaseLLM: An instance of the LLM.
        """
        config_to_use = llm_config if llm_config is not None else self.default_config
        # The llm_class constructor now expects model and llm_config as parameters
        return self.llm_class(model=self, llm_config=config_to_use)

    def __repr__(self):
        return (
            f"LLMModel(name='{self._name}', value='{self._value}', "
            f"canonical_name='{self._canonical_name}', "
            f"provider='{self.provider.name}', llm_class='{self.llm_class.__name__}')"
        )
    
    # __class_getitem__ is now handled by the metaclass LLMModelMeta's __getitem__
    # No need to define it here anymore.
