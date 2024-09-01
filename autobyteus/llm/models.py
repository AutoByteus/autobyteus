from enum import Enum
from autobyteus.llm.utils.llm_config import LLMConfig

class LLMModel(Enum):
    # ChatGPT models
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"

    # Mistral models
    MISTRAL_SMALL = "mistral-small"
    MISTRAL_MEDIUM = "mistral-medium"
    MISTRAL_LARGE = "mistral-large"

    # Groq models
    GEMMA_2_9B_IT = "gemma2-9b-it"
    GEMMA_7B_IT = "gemma-7b-it"
    LLAMA_3_1_405B_REASONING = "llama-3-1-405b-reasoning"
    LLAMA_3_1_70B_VERSATILE = "llama-3-1-70b-versatile"
    LLAMA_3_1_8B_INSTANT = "llama-3-1-8b-instant"
    LLAMA3_70B_8192 = "llama3-70b-8192"
    LLAMA3_8B_8192 = "llama3-8b-8192"
    MIXTRAL_8X7B_32768 = "mixtral-8x7b-32768"

    # Gemini models
    GEMINI_1_0_PRO = "gemini-1-0-pro"
    GEMINI_1_5_PRO = "gemini-1-5-pro"
    GEMINI_1_5_PRO_EXPERIMENTAL = "gemini-1-5-pro-experimental"
    GEMINI_1_5_FLASH = "gemini-1-5-flash"
    GEMMA_2_2B = "gemma-2-2b"
    GEMMA_2_9B = "gemma-2-9b"
    GEMMA_2_27B = "gemma-2-27b"

    # Claude models
    CLAUDE_3_HAIKU = "Claude3Haiku"
    CLAUDE_3_OPUS = "Claude3Opus"
    CLAUDE_3_5_SONNET = "Claude35Sonnet"

    # Perplexity models
    LLAMA_3_1_SONAR_LARGE_128K_ONLINE = "llama-3-1-sonar-large-128k-online"
    LLAMA_3_1_SONAR_SMALL_128K_ONLINE = "llama-3-1-sonar-small-128k-online"
    LLAMA_3_1_SONAR_LARGE_128K_CHAT = "llama-3-1-sonar-large-128k-chat"
    LLAMA_3_1_SONAR_SMALL_128K_CHAT = "llama-3-1-sonar-small-128k-chat"
    LLAMA_3_1_8B_INSTRUCT = "llama-3-1-8b-instruct"
    LLAMA_3_1_70B_INSTRUCT = "llama-3-1-70b-instruct"
    GEMMA_2_27B_IT = "gemma-2-27b-it"
    NEMOTRON_4_340B_INSTRUCT = "nemotron-4-340b-instruct"
    MIXTRAL_8X7B_INSTRUCT = "mixtral-8x7b-instruct"

    @property
    def default_config(self) -> LLMConfig:
        configs = {
            # ChatGPT models
            self.GPT_3_5_TURBO: LLMConfig(rate_limit=60, token_limit=4096),
            self.GPT_4: LLMConfig(rate_limit=40, token_limit=8192),

            # Mistral models
            self.MISTRAL_SMALL: LLMConfig(rate_limit=100, token_limit=32768),
            self.MISTRAL_MEDIUM: LLMConfig(rate_limit=80, token_limit=32768),
            self.MISTRAL_LARGE: LLMConfig(rate_limit=60, token_limit=32768),

            # Groq models
            self.GEMMA_2_9B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_7B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.LLAMA_3_1_405B_REASONING: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_70B_VERSATILE: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_8B_INSTANT: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA3_70B_8192: LLMConfig(rate_limit=60, token_limit=8192),
            self.LLAMA3_8B_8192: LLMConfig(rate_limit=60, token_limit=8192),
            self.MIXTRAL_8X7B_32768: LLMConfig(rate_limit=60, token_limit=32768),

            # Gemini models
            self.GEMINI_1_0_PRO: LLMConfig(rate_limit=60, token_limit=30720),
            self.GEMINI_1_5_PRO: LLMConfig(rate_limit=2, token_limit=30720),
            self.GEMINI_1_5_PRO_EXPERIMENTAL: LLMConfig(rate_limit=30, token_limit=30720),
            self.GEMINI_1_5_FLASH: LLMConfig(rate_limit=60, token_limit=16384),
            self.GEMMA_2_2B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_2_9B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_2_27B: LLMConfig(rate_limit=60, token_limit=8192),

            # Claude models
            self.CLAUDE_3_HAIKU: LLMConfig(rate_limit=60, token_limit=200000),
            self.CLAUDE_3_OPUS: LLMConfig(rate_limit=40, token_limit=200000),
            self.CLAUDE_3_5_SONNET: LLMConfig(rate_limit=50, token_limit=200000),

            # Perplexity models
            self.LLAMA_3_1_SONAR_LARGE_128K_ONLINE: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_SONAR_SMALL_128K_ONLINE: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_SONAR_LARGE_128K_CHAT: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_SONAR_SMALL_128K_CHAT: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_8B_INSTRUCT: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_70B_INSTRUCT: LLMConfig(rate_limit=60, token_limit=4096),
            self.GEMMA_2_27B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.NEMOTRON_4_340B_INSTRUCT: LLMConfig(rate_limit=40, token_limit=32768),
            self.MIXTRAL_8X7B_INSTRUCT: LLMConfig(rate_limit=60, token_limit=32768),
        }
        return configs.get(self, LLMConfig())