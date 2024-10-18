# file: autobyteus/llm/rpa/factory/rpa_llm_factory.py
from autobyteus.llm import llm_factory
from autobyteus.llm.models import LLMModel
from autobyteus.llm.rpa.chatgpt_llm import ChatGPTLLM
from autobyteus.llm.rpa.mistralchat_llm import MistralChatLLM
from autobyteus.llm.rpa.groqchat_llm import GroqChatLLM
from autobyteus.llm.rpa.geminichat_llm import GeminiChatLLM
from autobyteus.llm.rpa.claudechat_llm import ClaudeChatLLM
from autobyteus.llm.base_llm import BaseLLM
class RPALLMFactory(llm_factory):
    @staticmethod
    def create_llm(model: LLMModel) -> BaseLLM:
        if model in [LLMModel.GPT_4o, LLMModel.o1_MINI, LLMModel.o1_PREVIEW]:
            return ChatGPTLLM(model.value)
        elif model in [LLMModel.MISTRAL_SMALL, LLMModel.MISTRAL_MEDIUM, LLMModel.MISTRAL_LARGE]:
            return MistralChatLLM(model)
        elif model in [LLMModel.GEMMA_2_9B_IT, LLMModel.GEMMA_7B_IT, LLMModel.LLAMA_3_1_405B_REASONING,
                       LLMModel.LLAMA_3_1_70B_VERSATILE, LLMModel.LLAMA_3_1_8B_INSTANT, LLMModel.LLAMA3_70B_8192,
                       LLMModel.LLAMA3_8B_8192, LLMModel.MIXTRAL_8X7B_32768]:
            return GroqChatLLM(model)
        elif model == LLMModel.GEMINI_1_0_PRO:
            return GeminiChatLLM()
        elif model in [LLMModel.CLAUDE_3_HAIKU, LLMModel.CLAUDE_3_OPUS, LLMModel.CLAUDE_3_5_SONNET]:
            return ClaudeChatLLM(model)
        else:
            raise ValueError(f"Unsupported model: {model}")