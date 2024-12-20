from dataclasses import dataclass
from autobyteus.llm.models import LLMModel

@dataclass
class TokenPricing:
    input_price: float  # USD per 1000 tokens
    output_price: float  # USD per 1000 tokens

class TokenPricingRegistry:
    _prices = {
        # ChatGPT models
        LLMModel.GPT_4o_API: TokenPricing(0.0015, 0.002),
        LLMModel.o1_MINI_API: TokenPricing(0.03, 0.06),
        LLMModel.o1_API: TokenPricing(0.0015, 0.002),

        # Mistral models
        LLMModel.MISTRAL_SMALL_API: TokenPricing(0.0015, 0.0015),
        LLMModel.MISTRAL_MEDIUM_API: TokenPricing(0.002, 0.002),
        LLMModel.MISTRAL_LARGE_API: TokenPricing(0.003, 0.003),

        # Groq models
        LLMModel.GEMMA_2_9B_IT_API: TokenPricing(0.0005, 0.0005),
        LLMModel.GEMMA_7B_IT_API: TokenPricing(0.0007, 0.0007),
        LLMModel.LLAMA_3_1_405B_REASONING_API: TokenPricing(0.02, 0.02),
        LLMModel.LLAMA_3_1_70B_VERSATILE_API: TokenPricing(0.01, 0.01),
        LLMModel.LLAMA_3_1_8B_INSTANT_API: TokenPricing(0.0005, 0.0005),
        LLMModel.LLAMA3_70B_8192_API: TokenPricing(0.01, 0.01),
        LLMModel.LLAMA3_8B_8192_API: TokenPricing(0.0005, 0.0005),
        LLMModel.MIXTRAL_8X7B_32768_API: TokenPricing(0.001, 0.001),

        # Gemini models (updated)
        LLMModel.GEMINI_1_0_PRO_API: TokenPricing(0.00025, 0.0005),
        LLMModel.GEMINI_1_5_PRO_API: TokenPricing(0.0005, 0.001),
        LLMModel.GEMINI_1_5_PRO_EXPERIMENTAL_API: TokenPricing(0.0005, 0.001),
        LLMModel.GEMINI_1_5_FLASH_API: TokenPricing(0.0001, 0.0002),
        LLMModel.GEMMA_2_2B_API: TokenPricing(0.0001, 0.0002),
        LLMModel.GEMMA_2_9B_API: TokenPricing(0.0001, 0.0002),
        LLMModel.GEMMA_2_27B_API: TokenPricing(0.0001, 0.0002),

        # Claude models
        LLMModel.CLAUDE_3_HAIKU_API: TokenPricing(0.0015, 0.002),
        LLMModel.CLAUDE_3_OPUS_API: TokenPricing(0.03, 0.06),
        LLMModel.CLAUDE_3_5_SONNET_API: TokenPricing(0.002, 0.003),

        # Perplexity models
        LLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API: TokenPricing(0.001, 0.001),
        LLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API: TokenPricing(0.0005, 0.0005),
        LLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT_API: TokenPricing(0.001, 0.001),
        LLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT_API: TokenPricing(0.0005, 0.0005),
        LLMModel.LLAMA_3_1_8B_INSTRUCT_API: TokenPricing(0.0005, 0.0005),
        LLMModel.LLAMA_3_1_70B_INSTRUCT_API: TokenPricing(0.01, 0.01),
        LLMModel.GEMMA_2_27B_IT_API: TokenPricing(0.001, 0.001),
        LLMModel.NEMOTRON_4_340B_INSTRUCT_API: TokenPricing(0.02, 0.02),
        LLMModel.MIXTRAL_8X7B_INSTRUCT_API: TokenPricing(0.001, 0.001),
    }

    @classmethod
    def get_pricing(cls, model: LLMModel) -> TokenPricing:
        return cls._prices.get(model, TokenPricing(0, 0))