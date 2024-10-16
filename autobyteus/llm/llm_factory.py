from autobyteus.llm.api.bedrock.bedrock_chat_api import BedrockChat
from autobyteus.llm.api.claude.claude_chat_api import ClaudeChat
from autobyteus.llm.api.mistral.mistral_chat_api import MistralChat
from autobyteus.llm.api.openai.openai_chat_api import OpenAIChat
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

# Import all LLM implementations
from autobyteus.llm.rpa.chatgpt_llm import ChatGPTLLM
from autobyteus.llm.rpa.mistral_llm import MistralLLM
from autobyteus.llm.rpa.groq_llm import GroqLLM
from autobyteus.llm.rpa.gemini_llm import GeminiLLM
from autobyteus.llm.rpa.claudechat_llm import ClaudeChatLLM
from autobyteus.llm.rpa.perplexity_llm import PerplexityLLM

# Import API LLM implementations
class LLMFactory:
    @staticmethod
    def create_llm(model: LLMModel, custom_config: LLMConfig = None) -> BaseLLM:
        if model.is_api:
            return LLMFactory._create_api_llm(model, custom_config)
        else:
            return LLMFactory._create_rpa_llm(model, custom_config)

    @staticmethod
    def _create_rpa_llm(model: LLMModel, custom_config: LLMConfig = None) -> BaseLLM:
        if model in [LLMModel.GPT_4o, LLMModel.o1_MINI, LLMModel.o1_PREVIEW]:
            return ChatGPTLLM(model, custom_config)
        
        elif model in [LLMModel.MISTRAL_SMALL, LLMModel.MISTRAL_MEDIUM, LLMModel.MISTRAL_LARGE]:
            return MistralLLM(model, custom_config)
        elif model in [LLMModel.GEMMA_2_9B_IT, LLMModel.GEMMA_7B_IT, LLMModel.LLAMA_3_1_405B_REASONING,
                       LLMModel.LLAMA_3_1_70B_VERSATILE, LLMModel.LLAMA_3_1_8B_INSTANT, LLMModel.LLAMA3_70B_8192,
                       LLMModel.LLAMA3_8B_8192, LLMModel.MIXTRAL_8X7B_32768]:
            return GroqLLM(model, custom_config)
        elif model in [LLMModel.GEMINI_1_0_PRO, LLMModel.GEMINI_1_5_PRO, LLMModel.GEMINI_1_5_PRO_EXPERIMENTAL,
                       LLMModel.GEMINI_1_5_FLASH, LLMModel.GEMMA_2_2B, LLMModel.GEMMA_2_9B, LLMModel.GEMMA_2_27B]:
            return GeminiLLM(model, custom_config)
        elif model in [LLMModel.CLAUDE_3_HAIKU, LLMModel.CLAUDE_3_OPUS, LLMModel.CLAUDE_3_5_SONNET]:
            return ClaudeChatLLM(model, custom_config)
        elif model in [LLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE, LLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE,
                       LLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT, LLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT,
                       LLMModel.LLAMA_3_1_8B_INSTRUCT, LLMModel.LLAMA_3_1_70B_INSTRUCT,
                       LLMModel.GEMMA_2_27B_IT, LLMModel.NEMOTRON_4_340B_INSTRUCT, LLMModel.MIXTRAL_8X7B_INSTRUCT]:
            return PerplexityLLM(model, custom_config)
        else:
            raise ValueError(f"Unsupported RPA model: {model}")

    @staticmethod
    def _create_api_llm(model: LLMModel, custom_config: LLMConfig = None) -> BaseLLM:
        if model in [LLMModel.GPT_4o_API, LLMModel.o1_PREVIEW_API, LLMModel.o1_MINI_API, LLMModel.CHATGPT_4O_LATEST_API]:
            return OpenAIChat(model_name=model, system_message="you are a helpful assistant")
        elif model in [LLMModel.CLAUDE_3_HAIKU_API, LLMModel.CLAUDE_3_OPUS_API, LLMModel.CLAUDE_3_5_SONNET_API, LLMModel.CLAUDE_3_5_SONNET_LATEST_API]:
            return ClaudeChat(model_name=model, system_message="you are a helpful assistant")
        elif model in [LLMModel.MISTRAL_LARGE_API, LLMModel.MISTRAL_MEDIUM_API, LLMModel.MISTRAL_SMALL_API]:
            return MistralChat(model_name=model)
        elif model in [LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API]:
            return BedrockChat(model_name=model)
        else:
            raise ValueError(f"Unsupported API model: {model}")
