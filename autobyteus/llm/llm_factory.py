from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.api.openrouter_llm import OpenRouterLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.bedrock_llm import BedrockClaudeLLM
import pkg_resources
from typing import List, Callable, Tuple

class LLMFactory:
    _registry: dict[str, Tuple[type, Callable[[str], LLMModel]]] = {}

    @staticmethod
    def register_llm(model: str, llm_class: type, resolver: Callable[[str], LLMModel]):
        """
        Register an LLM model with its corresponding class and resolver.

        :param model: The name of the model.
        :param llm_class: The class to instantiate for this model.
        :param resolver: A callable that takes the model name and returns an LLMModel enum instance.
        """
        LLMFactory._registry[model] = (llm_class, resolver)

    @staticmethod
    def _initialize_registry():
        # Register main API LLMs using enum names and the main resolver
        LLMFactory.register_llm(LLMModel.GPT_4o_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.o1_PREVIEW_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.o1_MINI_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CHATGPT_4O_LATEST_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.GPT_3_5_TURBO_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.OPENROUTER_O1_MINI_API.name, OpenRouterLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.MISTRAL_SMALL_API.name, MistralLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.MISTRAL_MEDIUM_API.name, MistralLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.MISTRAL_LARGE_API.name, MistralLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_OPUS_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_SONNET_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_HAIKU_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_5_SONNET_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API.name, BedrockClaudeLLM, LLMModel.from_name)

        # Discover and register additional plugins
        LLMFactory._discover_plugins()

    @staticmethod
    def _discover_plugins():
        # Iterate over entry points in the 'autobyteus.plugins' group
        for entry_point in pkg_resources.iter_entry_points(group='autobyteus.plugins'):
            try:
                plugin_factory = entry_point.load()
                # Each plugin must have a 'register' method
                plugin_factory.register(LLMFactory.register_llm)
            except Exception as e:
                print(f"Failed to load plugin {entry_point.name}: {e}")

    @staticmethod
    def create_llm(model: str, custom_config: LLMConfig = None) -> BaseLLM:
        if model in LLMFactory._registry:
            llm_class, resolver = LLMFactory._registry[model]
            try:
                llm_model = resolver(model)
            except ValueError as e:
                raise ValueError(f"Invalid model name: {model}. Error: {str(e)}")
            return llm_class(llm_model, custom_config)
        else:
            raise ValueError(f"Unsupported model: {model}")

    @staticmethod
    def get_all_models() -> List[str]:
        """
        Returns a list of all registered model names.
        """
        return list(LLMFactory._registry.keys())

# Initialize the registry upon module import
LLMFactory._initialize_registry()