<<<<<<< Updated upstream
from autobyteus.llm.api.bedrock_llm import BedrockLLM
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.nvidia_llm import NvidiaLLM
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

import pkg_resources
from typing import List
=======
import pkg_resources
from autobyteus.llm.models import LLMModel as OriginalLLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

# Import API LLM implementations
from autobyteus.llm.api.chatgpt_llm import ChatGPTLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.groq_llm import GroqLLM
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.api.claudechat_llm import ClaudeChatLLM
from autobyteus.llm.api.perplexity_llm import PerplexityLLM
>>>>>>> Stashed changes

class LLMFactory:
    _registry = {}

    @staticmethod
<<<<<<< Updated upstream
    def _register_llm(model: str, llm_class):
        LLMFactory._registry[model] = llm_class

    @staticmethod
    def _initialize_registry():
        # Register main API LLMs using enum names
        LLMFactory._register_llm(LLMModel.NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.GPT_4o_API.name, OpenAILLM)
        LLMFactory._register_llm(LLMModel.o1_PREVIEW_API.name, OpenAILLM)
        LLMFactory._register_llm(LLMModel.o1_MINI_API.name, OpenAILLM)
        LLMFactory._register_llm(LLMModel.CHATGPT_4O_LATEST_API.name, OpenAILLM)
        LLMFactory._register_llm(LLMModel.GPT_3_5_TURBO_API.name, OpenAILLM)
        LLMFactory._register_llm(LLMModel.MISTRAL_SMALL_API.name, MistralLLM)
        LLMFactory._register_llm(LLMModel.MISTRAL_MEDIUM_API.name, MistralLLM)
        LLMFactory._register_llm(LLMModel.MISTRAL_LARGE_API.name, MistralLLM)
        LLMFactory._register_llm(LLMModel.GEMMA_2_9B_IT_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.GEMMA_7B_IT_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_405B_REASONING_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_70B_VERSATILE_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_8B_INSTANT_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.LLAMA3_70B_8192_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.LLAMA3_8B_8192_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.MIXTRAL_8X7B_32768_API.name, BedrockLLM)
        LLMFactory._register_llm(LLMModel.GEMINI_1_0_PRO_API.name, GeminiLLM)
        LLMFactory._register_llm(LLMModel.GEMINI_1_5_PRO_API.name, GeminiLLM)
        LLMFactory._register_llm(LLMModel.GEMINI_1_5_PRO_EXPERIMENTAL_API.name, GeminiLLM)
        LLMFactory._register_llm(LLMModel.GEMINI_1_5_FLASH_API.name, GeminiLLM)
        LLMFactory._register_llm(LLMModel.GEMMA_2_2B_API.name, GeminiLLM)
        LLMFactory._register_llm(LLMModel.GEMMA_2_9B_API.name, GeminiLLM)
        LLMFactory._register_llm(LLMModel.GEMMA_2_27B_API.name, GeminiLLM)
        LLMFactory._register_llm(LLMModel.CLAUDE_3_OPUS_API.name, ClaudeLLM)
        LLMFactory._register_llm(LLMModel.CLAUDE_3_SONNET_API.name, ClaudeLLM)
        LLMFactory._register_llm(LLMModel.CLAUDE_3_HAIKU_API.name, ClaudeLLM)
        LLMFactory._register_llm(LLMModel.CLAUDE_3_5_SONNET_API.name, ClaudeLLM)
        LLMFactory._register_llm(LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API.name, ClaudeLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_8B_INSTRUCT_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.LLAMA_3_1_70B_INSTRUCT_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.GEMMA_2_27B_IT_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.NEMOTRON_4_340B_INSTRUCT_API.name, NvidiaLLM)
        LLMFactory._register_llm(LLMModel.MIXTRAL_8X7B_INSTRUCT_API.name, NvidiaLLM)

        # Discover and register additional plugins
        LLMFactory._discover_plugins()

    @staticmethod
    def _discover_plugins():
        # Iterate over entry points in the 'autobyteus.plugins' group
        for entry_point in pkg_resources.iter_entry_points(group='autobyteus.plugins'):
            try:
                plugin_factory = entry_point.load()
                # Each plugin must have a 'register' method
                plugin_factory.register(LLMFactory._registry)
            except Exception as e:
                print(f"Failed to load plugin {entry_point.name}: {e}")

    @staticmethod
    def create_llm(model: str, custom_config: LLMConfig = None) -> BaseLLM:
        if model in LLMFactory._registry:
            llm_class = LLMFactory._registry[model]
            return llm_class(model, custom_config)
        else:
            raise ValueError(f"Unsupported model: {model}")

    @staticmethod
    def get_all_models() -> List[str]:
        """
        Returns a list of all registered model names.
        """
        return list(LLMFactory._registry.keys())
=======
    def _register_llm(model: OriginalLLMModel, llm_class):
        LLMFactory._registry[model] = llm_class

    @staticmethod
    def _initialize_registry():
        # Register API LLMs
        LLMFactory._register_llm(OriginalLLMModel.GPT_4o, ChatGPTLLM)
        LLMFactory._register_llm(OriginalLLMModel.o1_MINI, ChatGPTLLM)
        LLMFactory._register_llm(OriginalLLMModel.o1_PREVIEW, ChatGPTLLM)
        LLMFactory._register_llm(OriginalLLMModel.MISTRAL_SMALL, MistralLLM)
        LLMFactory._register_llm(OriginalLLMModel.MISTRAL_MEDIUM, MistralLLM)
        LLMFactory._register_llm(OriginalLLMModel.MISTRAL_LARGE, MistralLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_9B_IT, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_7B_IT, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_405B_REASONING, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_70B_VERSATILE, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_8B_INSTANT, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA3_70B_8192, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA3_8B_8192, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.MIXTRAL_8X7B_32768, GroqLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_0_PRO, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_5_PRO, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_5_PRO_EXPERIMENTAL, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_5_FLASH, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_2B, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_9B, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_27B, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.CLAUDE_3_HAIKU, ClaudeChatLLM)
        LLMFactory._register_llm(OriginalLLMModel.CLAUDE_3_OPUS, ClaudeChatLLM)
        LLMFactory._register_llm(OriginalLLMModel.CLAUDE_3_5_SONNET, ClaudeChatLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_8B_INSTRUCT, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_70B_INSTRUCT, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_27B_IT, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.NEMOTRON_4_340B_INSTRUCT, PerplexityLLM)
        LLMFactory._register_llm(OriginalLLMModel.MIXTRAL_8X7B_INSTRUCT, PerplexityLLM)

        # Discover and register plugins
        LLMFactory._discover_plugins()

    @staticmethod
    def _discover_plugins():
        # Iterate over entry points in the 'autobyteus.plugins' group
        for entry_point in pkg_resources.iter_entry_points(group='autobyteus.plugins'):
            try:
                plugin_factory = entry_point.load()
                # Each plugin must have a 'register' method
                plugin_factory.register(LLMFactory._registry)
            except Exception as e:
                print(f"Failed to load plugin {entry_point.name}: {e}")

    @staticmethod
    def create_llm(model: OriginalLLMModel, custom_config: LLMConfig = None) -> BaseLLM:
        if model in LLMFactory._registry:
            llm_class = LLMFactory._registry[model]
            return llm_class(model, custom_config)
        else:
            raise ValueError(f"Unsupported model: {model}")
>>>>>>> Stashed changes

# Initialize the registry upon module import
LLMFactory._initialize_registry()