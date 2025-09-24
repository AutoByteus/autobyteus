from typing import List, Set, Optional, Dict
import logging
import inspect

from autobyteus.llm.autobyteus_provider import AutobyteusModelProvider
from autobyteus.llm.models import LLMModel, ModelInfo, ProviderModelGroup
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from autobyteus.llm.base_llm import BaseLLM

from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.api.bedrock_llm import BedrockLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.api.deepseek_llm import DeepSeekLLM
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.api.grok_llm import GrokLLM
from autobyteus.llm.api.kimi_llm import KimiLLM
from autobyteus.llm.api.qwen_llm import QwenLLM
from autobyteus.llm.ollama_provider import OllamaModelProvider
from autobyteus.llm.lmstudio_provider import LMStudioModelProvider
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class LLMFactory(metaclass=SingletonMeta):
    _models_by_provider: Dict[LLMProvider, List[LLMModel]] = {}
    _models_by_identifier: Dict[str, LLMModel] = {}
    _initialized = False

    @staticmethod
    def ensure_initialized():
        """Ensures the factory is initialized before use."""
        if not LLMFactory._initialized:
            LLMFactory._initialize_registry()
            LLMFactory._initialized = True

    @staticmethod
    def reinitialize():
        """Reinitializes the model registry."""
        logger.info("Reinitializing LLM model registry...")
        LLMFactory._initialized = False
        LLMFactory._models_by_provider.clear()
        LLMFactory._models_by_identifier.clear()
        LLMFactory.ensure_initialized()
        logger.info("LLM model registry reinitialized successfully.")

    @staticmethod
    def _initialize_registry():
        """Initializes the registry with built-in models and discovers runtime models."""
        # Hardcoded direct-API models. Runtime defaults to API.
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
                name="gpt-5",
                value="gpt-5",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-5",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
                    pricing_config=TokenPricingConfig(1.25, 10.00)
                )
            ),
            LLMModel(
                name="gpt-5-mini",
                value="gpt-5-mini",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-5-mini",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
                    pricing_config=TokenPricingConfig(0.25, 2.00)
                )
            ),
            LLMModel(
                name="gpt-5-nano",
                value="gpt-5-nano",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-5-nano",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
                    pricing_config=TokenPricingConfig(0.05, 0.40)
                )
            ),
            LLMModel(
                name="gpt-5-chat-latest",
                value="gpt-5-chat-latest",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-5-chat-latest",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
                    pricing_config=TokenPricingConfig(1.25, 10.00)
                )
            ),
            LLMModel(
                name="gpt-4.1",
                value="gpt-4.1",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-4.1",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
                    pricing_config=TokenPricingConfig(2.00, 8.00)
                )
            ),
            LLMModel(
                name="gpt-4.1-mini",
                value="gpt-4.1-mini",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-4.1-mini",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
                    pricing_config=TokenPricingConfig(0.40, 1.60)
                )
            ),
            LLMModel(
                name="gpt-4.1-nano",
                value="gpt-4.1-nano",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="gpt-4.1-nano",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
                    pricing_config=TokenPricingConfig(0.10, 0.40)
                )
            ),
            LLMModel(
                name="o3",
                value="o3",
                provider=LLMProvider.OPENAI,
                llm_class=OpenAILLM,
                canonical_name="o3",
                default_config=LLMConfig(
                    uses_max_completion_tokens=True,
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
                    uses_max_completion_tokens=True,
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
                name="claude-4.1-opus",
                value="claude-opus-4-1-20250805",
                provider=LLMProvider.ANTHROPIC,
                llm_class=ClaudeLLM,
                canonical_name="claude-4.1-opus",
                default_config=LLMConfig(
                    # NOTE: Pricing is assumed to be the same as claude-4-opus
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
                name="bedrock-claude-4-opus",
                value="anthropic.claude-opus-4-20250514-v1:0",
                provider=LLMProvider.ANTHROPIC,
                llm_class=BedrockLLM,
                canonical_name="claude-4-opus",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(15.00, 75.00)
                )
            ),
            LLMModel(
                name="bedrock-claude-4.1-opus",
                value="anthropic.claude-opus-4-1-20250805-v1:0",
                provider=LLMProvider.ANTHROPIC,
                llm_class=BedrockLLM,
                canonical_name="claude-4.1-opus",
                default_config=LLMConfig(
                    # NOTE: Pricing is assumed to be the same as claude-4-opus
                    pricing_config=TokenPricingConfig(15.00, 75.00)
                )
            ),
            LLMModel(
                name="bedrock-claude-4-sonnet",
                value="anthropic.claude-sonnet-4-20250514-v1:0",
                provider=LLMProvider.ANTHROPIC,
                llm_class=BedrockLLM,
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
                llm_class=GeminiLLM,
                canonical_name="gemini-2.5-pro",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(2.50, 15.00)
                )
            ),
            LLMModel(
                name="gemini-2.5-flash",
                value="gemini-2.5-flash",
                provider=LLMProvider.GEMINI,
                llm_class=GeminiLLM,
                canonical_name="gemini-2.5-flash",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.30, 2.50)
                )
            ),
            LLMModel(
                name="gemini-2.5-flash-lite",
                value="gemini-2.5-flash-lite",
                provider=LLMProvider.GEMINI,
                llm_class=GeminiLLM,
                canonical_name="gemini-2.5-flash-lite",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.10, 0.40)
                )
            ),
            # KIMI Provider Models
            LLMModel(
                name="kimi-k2-0711-preview",
                value="kimi-k2-0711-preview",
                provider=LLMProvider.KIMI,
                llm_class=KimiLLM,
                canonical_name="kimi-k2-0711-preview",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.55, 2.21)
                )
            ),
            LLMModel(
                name="kimi-k2-0905-preview",
                value="kimi-k2-0905-preview",
                provider=LLMProvider.KIMI,
                llm_class=KimiLLM,
                canonical_name="kimi-k2-0905-preview",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(0.55, 2.21)
                )
            ),
            LLMModel(
                name="kimi-k2-turbo-preview",
                value="kimi-k2-turbo-preview",
                provider=LLMProvider.KIMI,
                llm_class=KimiLLM,
                canonical_name="kimi-k2-turbo-preview",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(2.76, 2.76)
                )
            ),
            LLMModel(
                name="kimi-latest",
                value="kimi-latest",
                provider=LLMProvider.KIMI,
                llm_class=KimiLLM,
                canonical_name="kimi-latest",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(1.38, 4.14)
                )
            ),
            LLMModel(
                name="kimi-thinking-preview",
                value="kimi-thinking-preview",
                provider=LLMProvider.KIMI,
                llm_class=KimiLLM,
                canonical_name="kimi-thinking-preview",
                default_config=LLMConfig(
                    pricing_config=TokenPricingConfig(27.59, 27.59)
                )
            ),
            # QWEN Provider Models
            LLMModel(
                name="qwen3-max",
                value="qwen-max",
                provider=LLMProvider.QWEN,
                llm_class=QwenLLM,
                canonical_name="qwen3-max",
                default_config=LLMConfig(
                    token_limit=262144,
                    pricing_config=TokenPricingConfig(
                        input_token_pricing=2.4,
                        output_token_pricing=12.0
                    )
                )
            ),
        ]
        for model in supported_models:
            LLMFactory.register_model(model)

        # Discover models from runtimes
        OllamaModelProvider.discover_and_register()
        LMStudioModelProvider.discover_and_register()
        AutobyteusModelProvider.discover_and_register()

    @staticmethod
    def register_model(model: LLMModel):
        """Registers a new LLM model."""
        identifier = model.model_identifier
        if identifier in LLMFactory._models_by_identifier:
            logger.debug(f"Redefining model with identifier '{identifier}'.")
            # Remove old model from provider group to replace it
            old_model = LLMFactory._models_by_identifier[identifier]
            if old_model.provider in LLMFactory._models_by_provider:
                # This check is needed because a model might be in _models_by_identifier but not yet in _models_by_provider if re-registering
                if old_model in LLMFactory._models_by_provider[old_model.provider]:
                    LLMFactory._models_by_provider[old_model.provider].remove(old_model)

        LLMFactory._models_by_identifier[identifier] = model
        LLMFactory._models_by_provider.setdefault(model.provider, []).append(model)

    @staticmethod
    def create_llm(model_identifier: str, llm_config: Optional[LLMConfig] = None) -> BaseLLM:
        """
        Creates an LLM instance for the specified unique model identifier.
        Raises an error if the identifier is not found or if a non-unique name is provided.
        """
        LLMFactory.ensure_initialized()
        
        # First, try a direct lookup by the unique model_identifier
        model = LLMFactory._models_by_identifier.get(model_identifier)
        if model:
            return model.create_llm(llm_config)

        # If not found, check if the user provided a non-unique name by mistake
        found_by_name = [m for m in LLMFactory._models_by_identifier.values() if m.name == model_identifier]
        if len(found_by_name) > 1:
            identifiers = [m.model_identifier for m in found_by_name]
            raise ValueError(
                f"The model name '{model_identifier}' is ambiguous. Please use one of the unique "
                f"model identifiers: {identifiers}"
            )
        
        raise ValueError(f"Model with identifier '{model_identifier}' not found.")

    # --- New Public API ---

    @staticmethod
    def list_available_models() -> List[ModelInfo]:
        """Returns a list of all available models with their detailed info."""
        LLMFactory.ensure_initialized()
        models = sorted(LLMFactory._models_by_identifier.values(), key=lambda m: m.model_identifier)
        return [
            ModelInfo(
                model_identifier=m.model_identifier,
                display_name=m.name,
                value=m.value,
                canonical_name=m.canonical_name,
                provider=m.provider.value,
                runtime=m.runtime.value,
                host_url=m.host_url
            )
            for m in models
        ]

    @staticmethod
    def list_models_by_provider(provider: LLMProvider) -> List[ModelInfo]:
        """Returns a list of available models for a specific provider."""
        LLMFactory.ensure_initialized()
        provider_models = sorted(
            [m for m in LLMFactory._models_by_identifier.values() if m.provider == provider],
            key=lambda m: m.model_identifier
        )
        return [
            ModelInfo(
                model_identifier=m.model_identifier,
                display_name=m.name,
                value=m.value,
                canonical_name=m.canonical_name,
                provider=m.provider.value,
                runtime=m.runtime.value,
                host_url=m.host_url
            )
            for m in provider_models
        ]

    @staticmethod
    def list_models_by_runtime(runtime: LLMRuntime) -> List[ModelInfo]:
        """Returns a list of available models for a specific runtime."""
        LLMFactory.ensure_initialized()
        runtime_models = sorted(
            [m for m in LLMFactory._models_by_identifier.values() if m.runtime == runtime],
            key=lambda m: m.model_identifier
        )
        return [
            ModelInfo(
                model_identifier=m.model_identifier,
                display_name=m.name,
                value=m.value,
                canonical_name=m.canonical_name,
                provider=m.provider.value,
                runtime=m.runtime.value,
                host_url=m.host_url
            )
            for m in runtime_models
        ]

    @staticmethod
    def get_canonical_name(model_identifier: str) -> Optional[str]:
        """
        Retrieves the canonical name for a given model identifier.
        """
        LLMFactory.ensure_initialized()
        model = LLMFactory._models_by_identifier.get(model_identifier)
        if model:
            return model.canonical_name
        
        logger.warning(f"Could not find model with identifier '{model_identifier}' to get its canonical name.")
        return None

default_llm_factory = LLMFactory()
