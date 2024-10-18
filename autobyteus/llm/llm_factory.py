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
from autobyteus.llm.models import LLMModel as OriginalLLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

class LLMFactory:
    _registry = {}

    @staticmethod
    def _register_llm(model: OriginalLLMModel, llm_class):
        LLMFactory._registry[model] = llm_class

    def _initialize_registry():
        # Register API LLMs
        LLMFactory._register_llm(OriginalLLMModel.GPT_4o, OpenAILLM)
        LLMFactory._register_llm(OriginalLLMModel.o1_MINI, OpenAILLM)
        LLMFactory._register_llm(OriginalLLMModel.o1_PREVIEW, OpenAILLM)
        LLMFactory._register_llm(OriginalLLMModel.MISTRAL_SMALL, MistralLLM)
        LLMFactory._register_llm(OriginalLLMModel.MISTRAL_MEDIUM, MistralLLM)
        LLMFactory._register_llm(OriginalLLMModel.MISTRAL_LARGE, MistralLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_9B_IT, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_7B_IT, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_405B_REASONING, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_70B_VERSATILE, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_8B_INSTANT, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA3_70B_8192, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA3_8B_8192, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.MIXTRAL_8X7B_32768, BedrockLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_0_PRO, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_5_PRO, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_5_PRO_EXPERIMENTAL, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMINI_1_5_FLASH, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_2B, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_9B, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_27B, GeminiLLM)
        LLMFactory._register_llm(OriginalLLMModel.CLAUDE_3_HAIKU, ClaudeLLM)
        LLMFactory._register_llm(OriginalLLMModel.CLAUDE_3_OPUS, ClaudeLLM)
        LLMFactory._register_llm(OriginalLLMModel.CLAUDE_3_5_SONNET, ClaudeLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_8B_INSTRUCT, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.LLAMA_3_1_70B_INSTRUCT, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.GEMMA_2_27B_IT, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.NEMOTRON_4_340B_INSTRUCT, NvidiaLLM)
        LLMFactory._register_llm(OriginalLLMModel.MIXTRAL_8X7B_INSTRUCT, NvidiaLLM)

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

# Initialize the registry upon module import
LLMFactory._initialize_registry()