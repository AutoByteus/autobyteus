from typing import List, Set, Optional, Dict
import logging
import pkg_resources
import inspect

from autobyteus.llm.autobyteus_provider import AutobyteusModelProvider
from autobyteus.llm.models import LLMModel
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

logger = logging.getLogger(__name__)

class LLMFactory:
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
    def _clear_model_class_attributes():
        """
        Clear all LLMModel instances that were set as class attributes on the LLMModel class.
        This is necessary for reinitialization to avoid 'model already exists' errors.
        """
        # Get all attributes of the LLMModel class
        for attr_name in list(vars(LLMModel).keys()):
            attr_value = getattr(LLMModel, attr_name)
            # Check if the attribute is an instance of LLMModel
            if isinstance(attr_value, LLMModel):
                logger.debug(f"Removing LLMModel class attribute: {attr_name}")
                # Delete the attribute to avoid 'model already exists' errors during reinitialization
                delattr(LLMModel, attr_name)

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
            
            # Clear all LLMModel instances set as class attributes
            LLMFactory._clear_model_class_attributes()
            
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
                value="o3-mini",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(1.0, 4.00)
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
                name="MISTRAL_LARGE_API",
                value="mistral-large-latest",
                provider=LLMProvider.MISTRAL,
                llm_class=MistralLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(2.00, 6.00)
                )
            ),
            # ANTHROPIC Provider Models
            LLMModel(
                name="CLAUDE_3_7_SONNET_API",
                value="claude-3-7-sonnet-20250219",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 15.00)
                )
            ),
            LLMModel(
                name="BEDROCK_CLAUDE_3_7_SONNET_API",
                value="anthropic.claude-3-7-sonnet-20250219-v1:0",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(3.00, 15.00)
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
                    pricing_config=TokenPricingConfig(0.014, 0.28)
                )
            ),
            # Adding deepseek-reasoner support
            LLMModel(
                name="DEEPSEEK_REASONER_API",
                value="deepseek-reasoner",
                provider=LLMProvider.DEEPSEEK,
                llm_class=DeepSeekLLM,
                default_config=LLMConfig(
                    rate_limit=60,
                    token_limit=8000,
                    pricing_config=TokenPricingConfig(0.14, 2.19)
                )
            ),
            # GEMINI Provider Models
            LLMModel(
                name="GEMINI_1_5_PRO_API",
                value="gemini-1-5-pro",
                provider=LLMProvider.GEMINI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(1.25, 5.00)
                )
            ),
            LLMModel(
                name="GEMINI_1_5_FLASH_API",
                value="gemini-1-5-flash",
                provider=LLMProvider.GEMINI,
                llm_class=OpenAILLM,
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.075, 0.30)
                )
            ),
            # GROK Provider Models
            LLMModel(
                name="GROK_2_1212_API",
                value="grok-2-1212",
                provider=LLMProvider.GROK,
                llm_class=GrokLLM,
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
        """
        models = LLMFactory._models_by_provider.setdefault(model.provider, [])
        models.append(model)

    @staticmethod
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
        LLMFactory.ensure_initialized()
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
