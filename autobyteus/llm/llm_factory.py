
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.api.ollama_llm import OllamaLLM
from autobyteus.llm.api.deepseek_llm import DeepSeekLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

import pkg_resources
from typing import List, Callable, Tuple, Dict, Set

class LLMFactory:
    _registry: Dict[str, Tuple[type, Callable[[str], LLMModel]]] = {}

    @staticmethod
    def register_llm(model: str, llm_class: type, resolver: Callable[[str], LLMModel]):
        LLMFactory._registry[model] = (llm_class, resolver)

    @staticmethod
    def _initialize_registry():
        # Register main API LLMs using enum names and the main resolver
        LLMFactory.register_llm(LLMModel.GPT_4o_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.o1_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.o1_MINI_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CHATGPT_4O_LATEST_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.GPT_3_5_TURBO_API.name, OpenAILLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.MISTRAL_SMALL_API.name, MistralLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.MISTRAL_MEDIUM_API.name, MistralLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.MISTRAL_LARGE_API.name, MistralLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_OPUS_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_SONNET_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_HAIKU_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.CLAUDE_3_5_SONNET_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API.name, ClaudeLLM, LLMModel.from_name)
        LLMFactory.register_llm(LLMModel.OLLAMA_LLAMA_3_2.name, OllamaLLM, LLMModel.from_name)