import logging
from typing import TYPE_CHECKING, Type, Optional, List, Iterator
from dataclasses import dataclass
from urllib.parse import urlparse

from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """A detailed public data structure for model information."""
    model_identifier: str
    display_name: str
    value: str
    canonical_name: str
    provider: str
    runtime: str
    host_url: Optional[str] = None

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
        from autobyteus.llm.llm_factory import LLMFactory
        LLMFactory.ensure_initialized()
        
        # Iterates over all registered models from the factory's internal dictionary
        for model in LLMFactory._models_by_identifier.values():
            yield model

    def __getitem__(cls, name_or_identifier: str) -> 'LLMModel':
        """
        Allows dictionary-like access to LLMModel instances by name or identifier.
        If a non-unique name is provided that matches multiple models, it raises an error.
        """
        from autobyteus.llm.llm_factory import LLMFactory
        factory = LLMFactory()
        factory.ensure_initialized()

        # First, try a direct lookup by unique model_identifier
        model = factory._models_by_identifier.get(name_or_identifier)
        if model:
            return model

        # If not found, search by name (which might not be unique)
        found_models = [m for m in factory._models_by_identifier.values() if m.name == name_or_identifier]

        if len(found_models) == 1:
            return found_models[0]
        
        if len(found_models) > 1:
            # Ambiguous name, guide the user to provide a unique identifier
            identifiers = [m.model_identifier for m in found_models]
            raise KeyError(
                f"Model name '{name_or_identifier}' is ambiguous and exists on multiple runtimes. "
                f"Please use one of the unique model identifiers: {identifiers}"
            )
        
        # If not found by identifier or name, raise KeyError
        available_models = list(factory._models_by_identifier.keys())
        raise KeyError(f"Model '{name_or_identifier}' not found. Available models are: {available_models}")

    def __len__(cls) -> int:
        """
        Allows getting the number of registered models (e.g., `len(LLMModel)`).
        """
        from autobyteus.llm.llm_factory import LLMFactory
        LLMFactory.ensure_initialized()
        return len(LLMFactory._models_by_identifier)

class LLMModel(metaclass=LLMModelMeta):
    """
    Represents a single model's metadata and connection properties.
    """

    def __init__(
        self,
        name: str,
        value: str,
        provider: LLMProvider,
        llm_class: Type["BaseLLM"],
        canonical_name: str,
        default_config: Optional[LLMConfig] = None,
        runtime: LLMRuntime = LLMRuntime.API,
        host_url: Optional[str] = None
    ):
        self._name = name
        self._value = value
        self._canonical_name = canonical_name
        self.provider = provider
        self.llm_class = llm_class
        self.default_config = default_config if default_config else LLMConfig()
        self.runtime = runtime
        self.host_url = host_url
        self._model_identifier = self._generate_identifier()

    def _generate_identifier(self) -> str:
        """Generates the globally unique model identifier."""
        if self.runtime == LLMRuntime.API:
            return self.name
        
        if not self.host_url:
            raise ValueError(f"host_url is required for runtime '{self.runtime.value}' on model '{self.name}'")
        
        try:
            parsed_url = urlparse(self.host_url)
            host_and_port = parsed_url.netloc
            return f"{self.name}:{self.runtime.value.lower()}@{host_and_port}"
        except Exception as e:
            logger.error(f"Failed to parse host_url '{self.host_url}' for identifier generation: {e}")
            # Fallback to a simpler, but still likely unique, identifier
            return f"{self.name}:{self.runtime.value.lower()}@{self.host_url}"

    @property
    def name(self) -> str:
        """
        The model's original name as expected by the runtime's API.
        Example: "llama3:latest", "gpt-4o"
        """
        return self._name

    @property
    def value(self) -> str:
        """
        The underlying unique identifier for this model (e.g. an API model string).
        Often the same as `name`. Example: "gpt-4o"
        """
        return self._value
    
    @property
    def model_identifier(self) -> str:
        """
        A globally unique, dynamically generated identifier for use within the system.
        Example: "llama3:latest:ollama@localhost:11434"
        """
        return self._model_identifier

    @property
    def canonical_name(self) -> str:
        """
        A standardized, shorter reference name for this model.
        Useful for prompt engineering and cross-referencing similar models.
        Example: "gpt-4o", "llama3"
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
        config_to_use = self.default_config
        if llm_config:
            # Create a copy to avoid modifying the default config
            config_to_use = LLMConfig.from_dict(self.default_config.to_dict())
            config_to_use.merge_with(llm_config)
            
        return self.llm_class(model=self, llm_config=config_to_use)

    def __repr__(self):
        return (
            f"LLMModel(identifier='{self.model_identifier}', name='{self.name}', "
            f"provider='{self.provider.name}', runtime='{self.runtime.name}')"
        )
