from typing import List, Set, Optional, Dict
import logging
import inspect

from autobyteus.llm.autobyteus_provider import AutobyteusModelProvider
from autobyteus.llm.models import LLMModel, ModelInfo, ProviderModelGroup
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from autobyteus.llm.base_llm import BaseLLM

from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.api.ollama_llm import OllamaLLM
from autobyteus.llm.api.deepseek_llm import DeepSeekLLM
from autobyteus.llm.api.grok_llm import GrokLLM
from autobyteus.llm.ollama_provider import OllamaModelProvider
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class LLMFactory(metaclass=SingletonMeta):
    _models_by_provider: Dict[LLMProvider, List[LLMModel]] = {}
    _initialized = False

    @staticmethod
    def register(model: LLMModel):
        LLMFactory.register_model(model)

    @staticmethod
    def ensure_initialized():
        """
        Ensures the factory is initialized before use.
        """
        if not LLMFactory._initialized:
            LLMFactory._initialize_registry()
            LLMFactory._initialized = True

    @staticmethod
    def reinitialize():
        """
        Reinitializes the model registry by resetting the initialization state
        and reinitializing the registry.
        
        This is useful when new provider API keys are configured and
        we need to discover models that might be available with the new keys.
        
        Returns:
            bool: True if reinitialization was successful, False otherwise.
        """
        try:
            logger.info("Reinitializing LLM model registry...")
            
            # Reset the initialized flag
            LLMFactory._initialized = False
            
            # Clear existing models registry
            LLMFactory._models_by_provider = {}
            
            # Reinitialize the registry
            LLMFactory.ensure_initialized()
            
            logger.info("LLM model registry reinitialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reinitialize LLM model registry: {str(e)}")
            return False

    @staticmethod
    def _initialize_registry():
        """
        Initialize the registry with supported models, discover plugins,
        organize models by provider, and assign models as attributes on LLMModel.
        """
        # Organize supported models by provider sections
        supported_models = [
            # OPENAI Provider Models
            LLMModel(
                name="gpt-4o",
                value="gpt-4o",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-4o",
                default_config=LLMConfig(
                    rate_limit=40, 
                    token_limit=8192,
                    pricing_config=TokenPricingConfig(2.50, 10.00)
                )
            ),
            LLMModel(
                name="o3",
                value="o3",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="o3",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(15.00, 60.00)
                )
            ),
            LLMModel(
                name="o4-mini",
                value="o4-mini",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="o4-mini",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(1.0, 4.00)
                )
            ),
            # MISTRAL Provider Models
            LLMModel(
                name="mistral-large",
                value="mistral-large-latest",
                provider=LLMProvider.MISTRAL,
                llm_class=MistralLLM,
                canonical_name="mistral-large",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(2.00, 6.00)
                )
            ),
            # ANTHROPIC Provider Models
            LLMModel(
                name="claude-4-opus",
                value="claude-opus-4-20250514",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                canonical_name="claude-4-opus",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(15.00, 75.00)
                )
            ),
            LLMModel(
                name="bedrock-claude-4-opus",
                value="anthropic.claude-opus-4-20250514-v1:0",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                canonical_name="claude-4-opus",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(15.00, 75.00)
                )
            ),
            LLMModel(
                name="claude-4-sonnet",
                value="claude-sonnet-4-20250514",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                canonical_name="claude-4-sonnet",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 15.00)
                )
            ),
            LLMModel(
                name="bedrock-claude-4-sonnet",
                value="anthropic.claude-sonnet-4-20250514-v1:0",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                canonical_name="claude-4-sonnet",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 15.00)
                )
            ),
            # DEEPSEEK Provider Models
            LLMModel(
                name="deepseek-chat",
                value="deepseek-chat",
                provider=LLMProvider.DEEPSEEK,
                llm_class=DeepSeekLLM,
                canonical_name="deepseek-chat",
                default_config=LLMConfig(
                    rate_limit=60,
                    token_limit=8000,
                    pricing_config=TokenPricingConfig(0.014, 0.28)
                )
            ),
            # Adding deepseek-reasoner support
            LLMModel(
                name="deepseek-reasoner",
                value="deepseek-reasoner",
                provider=LLMProvider.DEEPSEEK,
                llm_class=DeepSeekLLM,
                canonical_name="deepseek-reasoner",
                default_config=LLMConfig(
                    rate_limit=60,
                    token_limit=8000,
                    pricing_config=TokenPricingConfig(0.14, 2.19)
                )
            ),
            # GEMINI Provider Models
            LLMModel(
                name="gemini-2.5-pro",
                value="gemini-2.5-pro",
                provider=LLMProvider.GEMINI,
                llm_class=OpenAILLM,
                canonical_name="gemini-2.5-pro",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(2.50, 10.00)
                )
            ),
            LLMModel(
                name="gemini-2.5-flash",
                value="gemini-2.5-flash",
                provider=LLMProvider.GEMINI,
                llm_class=OpenAILLM,
                canonical_name="gemini-2.5-flash",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.15, 0.60)
                )
            ),
            LLMModel(
                name="gemini-2.0-flash",
                value="gemini-2.0-flash",
                provider=LLMProvider.GEMINI,
                llm_class=OpenAILLM,
                canonical_name="gemini-2.0-flash",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.1, 0.40)
                )
            ),
            LLMModel(
                name="gemini-2.0-flash-lite",
                value="gemini-2.0-flash-lite",
                provider=LLMProvider.GEMINI,
                llm_class=OpenAILLM,
                canonical_name="gemini-2.0-flash-lite",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.075, 0.30)
                )
            ),
            # GROK Provider Models
            LLMModel(
                name="grok-2-1212",
                value="grok-2-1212",
                provider=LLMProvider.GROK,
                llm_class=GrokLLM,
                canonical_name="grok-2",
                default_config=LLMConfig(
                    rate_limit=60,
                    token_limit=8000,
                    pricing_config=TokenPricingConfig(2.0, 6.0)
                )
            ),
        ]
        for model in supported_models:
            LLMFactory.register_model(model)

        OllamaModelProvider.discover_and_register()
        AutobyteusModelProvider.discover_and_register()

    @staticmethod
    def register_model(model: LLMModel):
        """
        Register a new LLM model, storing it under its provider category.
        If a model with the same name already exists, it will be replaced.
        """
        # Using a flat list of all models to check for existing model by name
        all_models = [m for models in LLMFactory._models_by_provider.values() for m in models]
        
        for existing_model in all_models:
            if existing_model.name == model.name:
                logger.warning(f"Model with name '{model.name}' is being redefined.")
                # Remove the old model from its provider list
                LLMFactory._models_by_provider[existing_model.provider].remove(existing_model)
                break

        models = LLMFactory._models_by_provider.setdefault(model.provider, [])
        models.append(model)

    @staticmethod
    def create_llm(model_identifier: str, llm_config: Optional[LLMConfig] = None) -> BaseLLM:
        """
        Create an LLM instance for the specified model identifier.
        
        Args:
            model_identifier (str): The model name to create an instance for.
            llm_config (Optional[LLMConfig]): Configuration for the LLM. If None,
                                             the model's default configuration is used.
        
        Returns:
            BaseLLM: An instance of the LLM.
        
        Raises:
            ValueError: If the model is not supported.
        """
        LLMFactory.ensure_initialized()
        for models in LLMFactory._models_by_provider.values():
            for model_instance in models:
                if model_instance.name == model_identifier:
                    return model_instance.create_llm(llm_config)
        raise ValueError(f"Unsupported model: {model_identifier}")

    @staticmethod
    def get_all_models() -> List[str]:
        """
        Returns a list of all registered model values.
        """
        LLMFactory.ensure_initialized()
        all_models = []
        for models in LLMFactory._models_by_provider.values():
            all_models.extend(model.name for model in models)
        return all_models

    @staticmethod
    def get_all_providers() -> Set[LLMProvider]:
        """
        Returns a set of all available LLM providers.
        """
        LLMFactory.ensure_initialized()
        return set(LLMProvider)

    @staticmethod
    def get_models_by_provider(provider: LLMProvider) -> List[str]:
        """
        Returns a list of all model values for a specific provider.
        """
        LLMFactory.ensure_initialized()
        return [model.value for model in LLMFactory._models_by_provider.get(provider, [])]

    @staticmethod
    def get_models_for_provider(provider: LLMProvider) -> List[LLMModel]:
        """
        Returns a list of LLMModel instances for a specific provider.
        """
        LLMFactory.ensure_initialized()
        return LLMFactory._models_by_provider.get(provider, [])

    @staticmethod
    def get_canonical_name(model_name: str) -> Optional[str]:
        """
        Get the canonical name for a model by its name.
        
        Args:
            model_name (str): The model name (e.g., "gpt_4o")
            
        Returns:
            Optional[str]: The canonical name if found, None otherwise
        """
        LLMFactory.ensure_initialized()
        for models in LLMFactory._models_by_provider.values():
            for model_instance in models:
                if model_instance.name == model_name:
                    return model_instance.canonical_name
        return None

    @staticmethod
    def get_models_grouped_by_provider() -> List[ProviderModelGroup]:
        """
        Returns a list of all providers, each with a list of its available models,
        sorted by provider name and model name. Providers with no models are included
        with an empty model list.
        """
        LLMFactory.ensure_initialized()
        result: List[ProviderModelGroup] = []
        # Sort all providers from the enum by name for consistent order
        all_providers_sorted = sorted(list(LLMProvider), key=lambda p: p.name)
        
        for provider in all_providers_sorted:
            # Get models for the current provider, defaults to [] if none are registered
            models = LLMFactory._models_by_provider.get(provider, [])
            
            # Sort the models for this provider by name
            sorted_models = sorted(models, key=lambda model: model.name)
            
            model_infos = [
                ModelInfo(name=model.name, canonical_name=model.canonical_name)
                for model in sorted_models
            ]
            
            result.append(ProviderModelGroup(
                provider=provider.name,
                models=model_infos
            ))
            
        return result

default_llm_factory = LLMFactory()
