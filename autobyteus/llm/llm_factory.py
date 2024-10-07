from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

# Import all LLM implementations
from autobyteus.llm.api.openai.openai_llm import OpenAI
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
        if model in [LLMModel.OpenAIRpaModels.GPT_4o, LLMModel.OpenAIRpaModels.o1_MINI, LLMModel.OpenAIRpaModels.o1_PREVIEW]:    
            return ChatGPTLLM(model, custom_config)
        
        elif model in [LLMModel.MistralRpaModels.MISTRAL_SMALL, LLMModel.MistralRpaModels.MISTRAL_MEDIUM, LLMModel.MistralRpaModels.MISTRAL_LARGE]:
            return MistralLLM(model, custom_config)
        elif model in [LLMModel.GroqRpaModels.GROQ_SMALL, LLMModel.GroqRpaModels.GROQ_MEDIUM, LLMModel.GroqRpaModels.GROQ_LARGE]:
            return GroqLLM(model, custom_config)
        elif model in [LLMModel.GeminiRpaModels.GEMINI_1_0_PRO, LLMModel.GeminiRpaModels.GEMINI_1_5_PRO, LLMModel.GeminiRpaModels.GEMINI_1_5_PRO_EXPERIMENTAL]:
            return GeminiLLM(model, custom_config)
        elif model in [LLMModel.ClaudeRpaModels.CLAUDE_3_HAIKU, LLMModel.ClaudeRpaModels.CLAUDE_3_OPUS, LLMModel.ClaudeRpaModels.CLAUDE_3_5_SONNET]:
            return ClaudeChatLLM(model, custom_config)
        elif model in [LLMModel.PerplexityRpaModels.PERPLEXITY_SMALL, LLMModel.PerplexityRpaModels.PERPLEXITY_MEDIUM, LLMModel.PerplexityRpaModels.PERPLEXITY_LARGE]:
            return PerplexityLLM(model, custom_config)
        else:
            raise ValueError(f"Unsupported RPA model: {model}")

    @staticmethod
    def _create_api_llm(model: LLMModel.OpenaiApiModels, custom_config: LLMConfig = None) -> BaseLLM:
        if model in [LLMModel.OpenaiApiModels.GPT_3_5_TURBO_API, LLMModel.OpenaiApiModels.GPT_4_API, LLMModel.OpenaiApiModels.GPT_4_0613_API, LLMModel.OpenaiApiModels.GPT_4o_API]:
            return OpenAI(model_name=model, config=custom_config)
        else:
            raise ValueError(f"Unsupported API model: {model}")
