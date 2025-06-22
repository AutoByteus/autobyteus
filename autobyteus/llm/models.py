import logging
from typing import TYPE_CHECKING, Type, Optional, List, Iterator

from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

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

        for attr_name in dir(cls):
            if not attr_name.startswith('_'):  # Skip private/dunder attributes
                attr_value = getattr(cls, attr_name)
                if isinstance(attr_value, cls):  # Check if it's an LLMModel instance
                    yield attr_value

    def __getitem__(cls, name_or_value: str) -> 'LLMModel':
        """
        Allows dictionary-like access to LLMModel instances by name (e.g., 'GPT_4o_API')
        or by value (e.g., 'gpt-4o').
        Search is performed by name first, then by value.
        """
        # Import LLMFactory locally to prevent circular import issues at module load time.
        from autobyteus.llm.llm_factory import LLMFactory
        LLMFactory.ensure_initialized()

        # 1. Try to find by name first (e.g., LLMModel['GPT_4o_API'])
        if hasattr(cls, name_or_value):
            attribute = getattr(cls, name_or_value)
            if isinstance(attribute, cls):
                return attribute
        
        # 2. If not found by name, iterate and find by value (e.g., LLMModel['gpt-4o'])
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
        for attr_name in dir(cls):
            if not attr_name.startswith('_'):
                attr_value = getattr(cls, attr_name)
                if isinstance(attr_value, cls):
                    count += 1
        return count

class LLMModel(metaclass=LLMModelMeta):
    """
    Represents a single model's metadata:
      - name (str): A human-readable label, e.g. "GPT-4 Official" 
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
        # Validate name doesn't already exist as a class attribute
        if hasattr(LLMModel, name):
            existing_model = getattr(LLMModel, name)
            if isinstance(existing_model, LLMModel):
                logger.warning(f"Model with name '{name}' is being redefined. This is expected during reinitialization.")
            
        self._name = name
        self._value = value
        self._canonical_name = canonical_name
        self.provider = provider
        self.llm_class = llm_class
        self.default_config = default_config if default_config else LLMConfig()

        # Set this instance as a class attribute, making LLMModel.MODEL_NAME available.
        logger.debug(f"Setting LLMModel class attribute: {name}")
        setattr(LLMModel, name, self)

    @property
    def name(self) -> str:
        """
        A friendly or descriptive name for this model (could appear in UI).
        This is the key used for `LLMModel['MODEL_NAME']` access.
        Example: "GPT_4o_API"
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
