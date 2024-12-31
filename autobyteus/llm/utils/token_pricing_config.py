
from dataclasses import dataclass
from autobyteus.llm.models import LLMModel

@dataclass
class TokenPricingConfig:
    """
    Represents the pricing configuration for input and output tokens.
    Prices are in USD per million tokens.
    """
    input_token_pricing: float  # USD per million tokens
    output_token_pricing: float  # USD per million tokens

class TokenPricingConfigRegistry:
    """
    Registry for token pricing configurations of different LLM models.
    Uses model names (enum values) as keys for simplicity.
    """
    _prices = {
        # ChatGPT models
        LLMModel.GPT_4o_API.value: TokenPricingConfig(0.0000015, 0.000002),
        LLMModel.o1_MINI_API.value: TokenPricingConfig(0.00003, 0.00006),
        LLMModel.o1_API.value: TokenPricingConfig(0.0000015, 0.000002),

        # Mistral models
        LLMModel.MISTRAL_SMALL_API.value: TokenPricingConfig(0.0000015, 0.0000015),
        LLMModel.MISTRAL_MEDIUM_API.value: TokenPricingConfig(0.000002, 0.000002),
        LLMModel.MISTRAL_LARGE_API.value: TokenPricingConfig(0.000003, 0.000003),

        # Groq models
        LLMModel.GEMMA_2_9B_IT_API.value: TokenPricingConfig(0.0000005, 0.0000005),
        LLMModel.GEMMA_7B_IT_API.value: TokenPricingConfig(0.0000007, 0.0000007),
        LLMModel.LLAMA_3_1_405B_REASONING_API.value: TokenPricingConfig(0.00002, 0.00002),
        LLMModel.LLAMA_3_1_70B_VERSATILE_API.value: TokenPricingConfig(0.00001, 0.00001),
        LLMModel.LLAMA_3_1_8B_INSTANT_API.value: TokenPricingConfig(0.0000005, 0.0000005),
        LLMModel.LLAMA3_70B_8192_API.value: TokenPricingConfig(0.00001, 0.00001),
        LLMModel.LLAMA3_8B_8192_API.value: TokenPricingConfig(0.0000005, 0.0000005),
        LLMModel.MIXTRAL_8X7B_32768_API.value: TokenPricingConfig(0.000001, 0.000001),

        # Gemini models
        LLMModel.GEMINI_1_0_PRO_API.value: TokenPricingConfig(0.00000025, 0.0000005),
        LLMModel.GEMINI_1_5_PRO_API.value: TokenPricingConfig(0.0000005, 0.000001),
        LLMModel.GEMINI_1_5_PRO_EXPERIMENTAL_API.value: TokenPricingConfig(0.0000005, 0.000001),
        LLMModel.GEMINI_1_5_FLASH_API.value: TokenPricingConfig(0.0000001, 0.0000002),
        LLMModel.GEMMA_2_2B_API.value: TokenPricingConfig(0.0000001, 0.0000002),
        LLMModel.GEMMA_2_9B_API.value: TokenPricingConfig(0.0000001, 0.0000002),
        LLMModel.GEMMA_2_27B_API.value: TokenPricingConfig(0.0000001, 0.0000002),

        # Claude models
        LLMModel.CLAUDE_3_HAIKU_API.value: TokenPricingConfig(0.0000015, 0.000002),
        LLMModel.CLAUDE_3_OPUS_API.value: TokenPricingConfig(0.00003, 0.00006),
        LLMModel.CLAUDE_3_5_SONNET_API.value: TokenPricingConfig(0.000002, 0.000003),

        # Perplexity models
        LLMModel.LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API.value: TokenPricingConfig(0.000001, 0.000001),
        LLMModel.LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API.value: TokenPricingConfig(0.0000005, 0.0000005),
        LLMModel.LLAMA_3_1_SONAR_LARGE_128K_CHAT_API.value: TokenPricingConfig(0.000001, 0.000001),
        LLMModel.LLAMA_3_1_SONAR_SMALL_128K_CHAT_API.value: TokenPricingConfig(0.0000005, 0.0000005),
        LLMModel.LLAMA_3_1_8B_INSTRUCT_API.value: TokenPricingConfig(0.0000005, 0.0000005),
        LLMModel.LLAMA_3_1_70B_INSTRUCT_API.value: TokenPricingConfig(0.00001, 0.00001),
        LLMModel.GEMMA_2_27B_IT_API.value: TokenPricingConfig(0.000001, 0.000001),
        LLMModel.NEMOTRON_4_340B_INSTRUCT_API.value: TokenPricingConfig(0.00002, 0.00002),
        LLMModel.MIXTRAL_8X7B_INSTRUCT_API.value: TokenPricingConfig(0.000001, 0.000001),
    }

    @classmethod
    def get_pricing(cls, model_name: str) -> TokenPricingConfig:
        """
        Get the token pricing configuration for a given model name.
        
        Args:
            model_name (str): The name of the model to get pricing for.
            
        Returns:
            TokenPricingConfig: The token pricing configuration for the model.
        """
        return cls._prices.get(model_name, TokenPricingConfig(0, 0))
