from enum import Enum
from autobyteus.llm.utils.llm_config import LLMConfig

class LLMModel(Enum):
    # OpenAI models
    GPT_4o_API = "gpt-4o"
    o1_PREVIEW_API = "o1-preview"
    o1_MINI_API = "o1-mini-api"
    CHATGPT_4O_LATEST_API = "chatgpt-4o-latest"  # No non-API counterpart found; retained original value
    GPT_3_5_TURBO_API = "gpt-3.5-turbo"

    # Mistral models
    MISTRAL_SMALL_API = "mistral-small"
    MISTRAL_MEDIUM_API = "mistral-medium"
    MISTRAL_LARGE_API = "mistral-large"

    # Claude models
    CLAUDE_3_OPUS_API = "claude-3-opus-20240229"
    CLAUDE_3_SONNET_API = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU_API = "claude-3-haiku-20240307"
    CLAUDE_3_5_SONNET_API = "claude-3-5-sonnet-20240620"
    BEDROCK_CLAUDE_3_5_SONNET_API = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # No non-API counterpart found; retained original value

    @property
    def default_config(self) -> LLMConfig:
        configs = {
            # OpenAI models
            self.GPT_4o_API: LLMConfig(rate_limit=40, token_limit=8192),
            self.o1_PREVIEW_API: LLMConfig(rate_limit=50, token_limit=16384),  # Adjust these values
            self.o1_MINI_API: LLMConfig(rate_limit=60, token_limit=4096),      # Adjust these values
            self.CHATGPT_4O_LATEST_API: LLMConfig(rate_limit=40, token_limit=8192),
            self.GPT_3_5_TURBO_API: LLMConfig(rate_limit=40, token_limit=4096),

            # Mistral models
            self.MISTRAL_SMALL_API: LLMConfig(rate_limit=100, token_limit=32768),
            self.MISTRAL_MEDIUM_API: LLMConfig(rate_limit=80, token_limit=32768),
            self.MISTRAL_LARGE_API: LLMConfig(rate_limit=60, token_limit=32768),

            # Claude models
            self.CLAUDE_3_OPUS_API: LLMConfig(rate_limit=40, token_limit=200000),
            self.CLAUDE_3_SONNET_API: LLMConfig(rate_limit=50, token_limit=200000),
            self.CLAUDE_3_HAIKU_API: LLMConfig(rate_limit=60, token_limit=200000),
            self.CLAUDE_3_5_SONNET_API: LLMConfig(rate_limit=50, token_limit=200000),
            self.BEDROCK_CLAUDE_3_5_SONNET_API: LLMConfig(rate_limit=50, token_limit=200000),
        }
        return configs.get(self, LLMConfig())

    @property
    def is_api(self) -> bool:
        return self.name.endswith('_API')
    
    @classmethod
    def from_name(cls, name: str) -> 'LLMModel':
        try:
            return cls[name]
        except KeyError:
            raise ValueError(f"Invalid LLMModel name: {name}")