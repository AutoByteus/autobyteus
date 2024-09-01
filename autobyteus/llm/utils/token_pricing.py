from dataclasses import dataclass
from autobyteus.llm.models import LLMModel

@dataclass
class TokenPricing:
    input_price: float  # USD per 1000 tokens
    output_price: float  # USD per 1000 tokens

class TokenPricingRegistry:
    _prices = {
        # ChatGPT models
        LLMModel.GPT_3_5_TURBO: TokenPricing(0.0015, 0.002),
        LLMModel.GPT_4: TokenPricing(0.03, 0.06),

        # Mistral models
        LLMModel.MISTRAL_SMALL: TokenPricing(0.0015, 0.0015),  # Example price, adjust as needed
        LLMModel.MISTRAL_MEDIUM: TokenPricing(0.002, 0.002),   # Example price, adjust as needed
        LLMModel.MISTRAL_LARGE: TokenPricing(0.003, 0.003),    # Example price, adjust as needed

        # Groq models
        LLMModel.GEMMA_2_9B_IT: TokenPricing(0.0005, 0.0005),  # Example price, adjust as needed
        LLMModel.GEMMA_7B_IT: TokenPricing(0.0007, 0.0007),    # Example price, adjust as needed
        LLMModel.LLAMA_3_1_405B_REASONING: TokenPricing(0.02, 0.02),  # Example price, adjust as needed
        LLMModel.LLAMA_3_1_70B_VERSATILE: TokenPricing(0.01, 0.01),   # Example price, adjust as needed
        LLMModel.LLAMA_3_1_8B_INSTANT: TokenPricing(0.0005, 0.0005),  # Example price, adjust as needed
        LLMModel.LLAMA3_70B_8192: TokenPricing(0.01, 0.01),    # Example price, adjust as needed
        LLMModel.LLAMA3_8B_8192: TokenPricing(0.0005, 0.0005), # Example price, adjust as needed
        LLMModel.MIXTRAL_8X7B_32768: TokenPricing(0.001, 0.001),  # Example price, adjust as needed

        # Gemini models
        LLMModel.GEMINI_1_0_PRO: TokenPricing(0.001, 0.001),   # Example price, adjust as needed
        LLMModel.GEMINI_1_5_PRO: TokenPricing(0.0015, 0.0015), # Example price, adjust as needed
        LLMModel.GEMINI_1_5_PRO_EXPERIMENTAL: TokenPricing(0.002, 0.002), # Example price, adjust as needed
        LLMModel.GEMINI_1_5_FLASH: TokenPricing(0.0005, 0.0005),  # Example price, adjust as needed
        LLMModel.GEMMA_2_2B: TokenPricing(0.0003, 0.0003),     # Example price, adjust as needed
        LLMModel.GEMMA_2_9B: TokenPricing(0.0005, 0.0005),     # Example price, adjust as needed
        LLMModel.GEMMA_2_27B: TokenPricing(0.001, 0.001),      # Example price, adjust as needed

        # Claude models
        LLMModel.CLAUDE_3_HAIKU: TokenPricing(0.0015, 0.002),  # Example price, adjust as needed
        LLMModel.CLAUDE_3_OPUS: TokenPricing(0.03, 0.06),      # Example price, adjust as needed
        LLMModel.CLAUDE_3_5_SONNET: TokenPricing(0.002, 0.003),  # Example price, adjust as needed

        # Perplexity models
        LLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE: TokenPricing(0.001, 0.001),  # Example price, adjust as needed
        LLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE: TokenPricing(0.0005, 0.0005),  # Example price, adjust as needed
        LLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT: TokenPricing(0.001, 0.001),  # Example price, adjust as needed
        LLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT: TokenPricing(0.0005, 0.0005),  # Example price, adjust as needed
        LLMModel.LLAMA_3_1_8B_INSTRUCT: TokenPricing(0.0005, 0.0005),  # Example price, adjust as needed
        LLMModel.LLAMA_3_1_70B_INSTRUCT: TokenPricing(0.01, 0.01),  # Example price, adjust as needed
        LLMModel.GEMMA_2_27B_IT: TokenPricing(0.001, 0.001),  # Example price, adjust as needed
        LLMModel.NEMOTRON_4_340B_INSTRUCT: TokenPricing(0.02, 0.02),  # Example price, adjust as needed
        LLMModel.MIXTRAL_8X7B_INSTRUCT: TokenPricing(0.001, 0.001),  # Example price, adjust as needed
    }

    @classmethod
    def get_pricing(cls, model: LLMModel) -> TokenPricing:
        return cls._prices.get(model, TokenPricing(0, 0))