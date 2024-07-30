from autobyteus.llm.models import LLMModel
from autobyteus.llm.rpa.chatgpt_llm import ChatGPTLLM
from autobyteus.llm.rpa.mistral_llm import MistralLLM
from autobyteus.llm.rpa.groq_llm import GroqLLM
from autobyteus.llm.rpa.gemini_llm import GeminiLLM
from autobyteus.llm.rpa.claudechat_llm import ClaudeChatLLM
from autobyteus.llm.base_llm import BaseLLM

class RPALLMFactory:
    @staticmethod
    def create_llm(model: LLMModel) -> BaseLLM:
        if model in [LLMModel.GPT_3_5_TURBO, LLMModel.GPT_4]:
            return ChatGPTLLM(model.value)
        elif model in [LLMModel.MISTRAL_SMALL, LLMModel.MISTRAL_MEDIUM, LLMModel.MISTRAL_LARGE]:
            return MistralLLM(model)
        elif model in [LLMModel.GEMMA_2_9B_IT, LLMModel.GEMMA_7B_IT, LLMModel.LLAMA_3_1_405B_REASONING,
                       LLMModel.LLAMA_3_1_70B_VERSATILE, LLMModel.LLAMA_3_1_8B_INSTANT, LLMModel.LLAMA3_70B_8192,
                       LLMModel.LLAMA3_8B_8192, LLMModel.MIXTRAL_8X7B_32768]:
            return GroqLLM(model)
        elif model == LLMModel.GEMINI:
            return GeminiLLM()
        elif model in [LLMModel.CLAUDE_3_HAIKU, LLMModel.CLAUDE_3_OPUS, LLMModel.CLAUDE_3_5_SONNET]:
            return ClaudeChatLLM(model)
        else:
            raise ValueError(f"Unsupported model: {model}")