from autobyteus.llm.api.bedrock_llm import BedrockLLM
from autobyteus.llm.api.claude_llm import ClaudeLLM
from autobyteus.llm.api.gemini_llm import GeminiLLM
from autobyteus.llm.api.mistral_llm import MistralLLM
from autobyteus.llm.api.nvidia_llm import NvidiaLLM
from autobyteus.llm.api.openai_llm import OpenAILLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

# Import all LLM implementations
from autobyteus.llm.rpa.chatgpt_llm import ChatGPTLLM
from autobyteus.llm.rpa.mistralchat_llm import MistralChatLLM
from autobyteus.llm.rpa.groqchat_llm import GroqChatLLM
from autobyteus.llm.rpa.geminichat_llm import GeminiChatLLM
from autobyteus.llm.rpa.claudechat_llm import ClaudeChatLLM
from autobyteus.llm.rpa.perplexitychat_llm import PerplexityChatLLM

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
            return MistralChatLLM(model, custom_config)
        
        elif model in [
            LLMModel.GEMMA_2_9B_IT, LLMModel.GEMMA_7B_IT, LLMModel.LLAMA_3_1_405B_REASONING,
            LLMModel.LLAMA_3_1_70B_VERSATILE, LLMModel.LLAMA_3_1_8B_INSTANT, LLMModel.LLAMA3_70B_8192,
            LLMModel.LLAMA3_8B_8192, LLMModel.MIXTRAL_8X7B_32768
        ]:
            return GroqChatLLM(model, custom_config)
        
        elif model in [
            LLMModel.GEMINI_1_0_PRO, LLMModel.GEMINI_1_5_PRO, LLMModel.GEMINI_1_5_PRO_EXPERIMENTAL,
            LLMModel.GEMINI_1_5_FLASH, LLMModel.GEMMA_2_2B, LLMModel.GEMMA_2_9B, LLMModel.GEMMA_2_27B
        ]:
            return GeminiChatLLM(model, custom_config)
        
        elif model in [LLMModel.CLAUDE_3_HAIKU, LLMModel.CLAUDE_3_OPUS, LLMModel.CLAUDE_3_5_SONNET]:
            return ClaudeChatLLM(model, custom_config)
        
        elif model in [
            LLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE, LLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE,
            LLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT, LLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT,
            LLMModel.LLAMA_3_1_8B_INSTRUCT, LLMModel.LLAMA_3_1_70B_INSTRUCT,
            LLMModel.GEMMA_2_27B_IT, LLMModel.NEMOTRON_4_340B_INSTRUCT, LLMModel.MIXTRAL_8X7B_INSTRUCT
        ]:
            return PerplexityChatLLM(model, custom_config)
        
        else:
            raise ValueError(f"Unsupported RPA model: {model}")

    @staticmethod
    def _create_api_llm(model: LLMModel, custom_config: LLMConfig = None) -> BaseLLM:
        if model in [
            LLMModel.GPT_4o_API, LLMModel.o1_PREVIEW_API, LLMModel.o1_MINI_API,
            LLMModel.CHATGPT_4O_LATEST_API, LLMModel.GPT_3_5_TURBO_API
        ]:
            return OpenAILLM(model_name=model, system_message="You are a helpful assistant.")
        
        elif model in [
            LLMModel.CLAUDE_3_HAIKU_API, LLMModel.CLAUDE_3_OPUS_API, 
            LLMModel.CLAUDE_3_5_SONNET_API, LLMModel.CLAUDE_3_HAIKU_API
        ]:
            return ClaudeLLM(model_name=model, system_message="You are a helpful assistant.")
        
        elif model in [LLMModel.MISTRAL_LARGE_API, LLMModel.MISTRAL_MEDIUM_API, LLMModel.MISTRAL_SMALL_API]:
            return MistralLLM(model_name=model)
        
        elif model in [LLMModel.BEDROCK_CLAUDE_3_5_SONNET_API]:
            return BedrockLLM(model_name=model)
        
        elif model in [
            LLMModel.GEMINI_1_5_FLASH_API, LLMModel.GEMINI_1_5_PRO_API, LLMModel.GEMINI_1_0_PRO_API
        ]:
            return GeminiLLM(model_name=model)
        
        elif model in [LLMModel.NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API]:
            return NvidiaLLM(model_name=model)
        
        else:
            raise ValueError(f"Unsupported API model: {model}")