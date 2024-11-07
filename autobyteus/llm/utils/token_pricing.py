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
        LLMModel.o1_PREVIEW_API: TokenPricing(0.0015, 0.002),

        # Mistral models
        LLMModel.MISTRAL_SMALL_API: TokenPricing(0.0015, 0.0015),
        LLMModel.MISTRAL_MEDIUM_API: TokenPricing(0.002, 0.002),
        LLMModel.MISTRAL_LARGE_API: TokenPricing(0.003, 0.003),

        # Claude models
        LLMModel.CLAUDE_3_HAIKU_API: TokenPricing(0.0015, 0.002),
        LLMModel.CLAUDE_3_OPUS_API: TokenPricing(0.03, 0.06),
        LLMModel.CLAUDE_3_5_SONNET_API: TokenPricing(0.002, 0.003),
    }

    @classmethod
    def get_pricing(cls, model: LLMModel) -> TokenPricing:
        return cls._prices.get(model, TokenPricing(0, 0))