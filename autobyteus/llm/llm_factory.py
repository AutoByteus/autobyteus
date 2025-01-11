from typing import List, Set, Optional, Dict
import logging
import pkg_resources

from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from autobyteus.llm.base_llm import BaseLLM

from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.api.ollama_llm import OllamaLLM
from autobyteus.llm.api.deepseek_llm import DeepSeekLLM

logger = logging.getLogger(__name__)

class LLMFactory:
    _models_by_provider: Dict[LLMProvider, List[LLMModel]] = {}

    @staticmethod
    def _initialize_registry():
        """
        Initialize the registry with supported models, discover plugins,
        organize models by provider, and assign models as attributes on LLMModel.
        """
        # Organize supported models by provider sections
        supported_models = [
            # NVIDIA Provider Models
            LLMModel(
                name="NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API",
                value="nvidia/llama-3.1-nemotron-70b-instruct",
                provider=LLMProvider.NVIDIA,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    rate_limit=60, 
                    token_limit=32768,
                    pricing_config=TokenPricingConfig(0.00002, 0.00002)
                )
            ),
            # OPENAI Provider Models
            LLMModel(
                name="GPT_4o_API",
                value="gpt-4o",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    rate_limit=40, 
                    token_limit=8192,
                    pricing_config=TokenPricingConfig(2.50, 10.00)
                )
            ),
            LLMModel(
                name="o1_API",
                value="o1",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(15.00, 60.00)
                )
            ),
            LLMModel(
                name="o1_MINI_API",
                value="o1-mini",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 12.00)
                )
            ),
            LLMModel(
                name="CHATGPT_4O_LATEST_API",
                value="chatgpt-4o-latest",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(2.50, 10.00)
                )
            ),
            LLMModel(
                name="GPT_3_5_TURBO_API",
                value="gpt-3.5-turbo",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(1.50, 2.00)
                )
            ),
            # MISTRAL Provider Models
            LLMModel(
                name="MISTRAL_SMALL_API",
                value="mistral-small-latest",
                provider=LLMProvider.MISTRAL,
                llm_class=MistralLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.20, 0.60)
                )
            ),
            LLMModel(
                name="MISTRAL_MEDIUM_API",
                value="mistral-medium",
                provider=LLMProvider.MISTRAL,
                llm_class=MistralLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.20, 0.60)
                )
            ),
            LLMModel(
                name="MISTRAL_LARGE_API",
                value="mistral-large",
                provider=LLMProvider.MISTRAL,
                llm_class=MistralLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(2.00, 6.00)
                )
            ),
            # ANTHROPIC Provider Models
            LLMModel(
                name="CLAUDE_3_OPUS_API",
                value="claude-3-opus-20240229",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(15.00, 75.00)
                )
            ),
            LLMModel(
                name="CLAUDE_3_SONNET_API",
                value="claude-3-sonnet-20240229",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 15.00)
                )
            ),
            LLMModel(
                name="CLAUDE_3_HAIKU_API",
                value="claude-3-haiku-20240307",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.25, 1.25)
                )
            ),
            LLMModel(
                name="CLAUDE_3_5_SONNET_API",
                value="claude-3-5-sonnet-20240620",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 15.00)
                )
            ),
            LLMModel(
                name="BEDROCK_CLAUDE_3_5_SONNET_API",
                value="anthropic.claude-3-5-sonnet-20240620-v1:0",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 15.00)
                )
            ),
            # OLLAMA Provider Models
            LLMModel(
                name="OLLAMA_LLAMA_3_2",
                value="llama3.2",
                provider=LLMProvider.OLLAMA,
                llm_class=OllamaLLM,
                default_config=LLMConfig(
                    rate_limit=60,
                    token_limit=8192,
                    pricing_config=TokenPricingConfig(0.0, 0.0)
                )
            ),
            # DEEPSEEK Provider Models
            LLMModel(
                name="DEEPSEEK_CHAT_API",
                value="deepseek-chat",
                provider=LLMProvider.DEEPSEEK,
                llm_class=DeepSeekLLM,
                default_config=LLMConfig(
                    rate_limit=60,
                    token_limit=8000,
                    pricing_config=TokenPricingConfig(0.14, 0.28)
                )
            ),
            # Add additional supported models as needed, following the pattern
        ]
        for model in supported_models:
            LLMFactory.register_model(model)

        # Discover and register plugin models
        LLMFactory._discover_plugins()

        # Dynamically assign each model as a class attribute on LLMModel for enum-like access
        for provider_models in LLMFactory._models_by_provider.values():
            for model in provider_models:
                setattr(LLMModel, model.name, model)

    @staticmethod
    def _discover_plugins():
        """
        Discover plugins registered under the 'autobyteus.plugins' entry point.
        Plugins can register new models using LLMFactory.register_model.
        """
        for entry_point in pkg_resources.iter_entry_points(group='autobyteus.plugins'):
            try:
                plugin_factory = entry_point.load()
                # Each plugin must have a 'register' method accepting a register function
                plugin_factory.register(LLMFactory.register_model)
            except Exception as e:
                logger.error(f"Failed to load plugin {entry_point.name}: {e}")

    @staticmethod
    def register_model(model: LLMModel):
        """
        Register a new LLM model, storing it under its provider category.
        """
        models = LLMFactory._models_by_provider.setdefault(model.provider, [])
        models.append(model)

    def create_llm(model: str, custom_config: Optional[LLMConfig] = None) -> BaseLLM:
        """
        Create an LLM instance for the specified model name.
        
        Args:
            model (str): The model name to create an instance for.
                         This corresponds to the original enum name.
            custom_config (Optional[LLMConfig]): Optional custom configuration for the LLM.
        
        Returns:
            BaseLLM: An instance of the LLM.
        
        Raises:
            ValueError: If the model is not supported.
        
        Note:
            Although the parameter is named 'model', it refers to the model's name, not its value.
        """
        for models in LLMFactory._models_by_provider.values():
            for model_instance in models:
                if model_instance.value == model or model_instance.name == model:
                    return model_instance.create_llm(custom_config)
        raise ValueError(f"Unsupported model: {model}")

    @staticmethod
    def get_all_models() -> List[str]:
        """
        Returns a list of all registered model values.
        """
        all_models = []
        for models in LLMFactory._models_by_provider.values():
            all_models.extend(model.name for model in models)
        return all_models

    @staticmethod
    def get_all_providers() -> Set[LLMProvider]:
        """
        Returns a set of all available LLM providers.
        """
        return set(LLMFactory._models_by_provider.keys())

    @staticmethod
    def get_models_by_provider(provider: LLMProvider) -> List[str]:
        """
        Returns a list of all model values for a specific provider.
        """
        return [model.value for model in LLMFactory._models_by_provider.get(provider, [])]

    @staticmethod
    def get_models_for_provider(provider: LLMProvider) -> List[LLMModel]:
        """
        Returns a list of LLMModel instances for a specific provider.
        """
        return LLMFactory._models_by_provider.get(provider, [])

# Initialize the registry upon module import
LLMFactory._initialize_registry()
