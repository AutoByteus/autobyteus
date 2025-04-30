import logging
from typing import TYPE_CHECKING, Type, Optional
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

logger = logging.getLogger(__name__)

class LLMModel:
    """
    Represents a single model's metadata:
      - name (str): A human-readable label, e.g. "GPT-4 Official" 
      - value (str): A unique identifier used in code or APIs, e.g. "gpt-4o"
      - provider (LLMProvider): The provider enum 
      - llm_class (Type[BaseLLM]): Which Python class to instantiate 
      - default_config (LLMConfig): Default configuration (token limit, etc.)

    Each model also exposes a create_llm() method to instantiate the underlying class.
    """

    def __init__(
        self,
        name: str,
        value: str,
        provider: LLMProvider,
        llm_class: Type["BaseLLM"],
        default_config: Optional[LLMConfig] = None
    ):
        # Validate name doesn't already exist as a class attribute
        if hasattr(LLMModel, name):
            existing_model = getattr(LLMModel, name)
            if isinstance(existing_model, LLMModel):
                raise ValueError(f"Model with name '{name}' already exists")
            
        self._name = name
        self._value = value
        self.provider = provider
        self.llm_class = llm_class
        self.default_config = default_config if default_config else LLMConfig()

        # Set this instance as a class attribute
        logger.debug(f"Setting LLMModel class attribute: {name}")
        setattr(LLMModel, name, self)

    @property
    def name(self) -> str:
        """
        A friendly or descriptive name for this model (could appear in UI).
        """
        return self._name

    @property
    def value(self) -> str:
        """
        The underlying unique identifier for this model (e.g. an API model string).
        """
        return self._value

    def create_llm(self, custom_config: Optional[LLMConfig] = None) -> "BaseLLM":
        """
        Instantiate the LLM class for this model, applying
        an optional custom_config override if supplied.
        """
        config_to_use = custom_config if custom_config else self.default_config
        return self.llm_class(model=self, custom_config=config_to_use)

    def __repr__(self):
        return (
            f"LLMModel(name='{self._name}', value='{self._value}', "
            f"provider='{self.provider.name}', llm_class='{self.llm_class.__name__}')"
        )
