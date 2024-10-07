from enum import Enum
from autobyteus.llm.utils.llm_config import LLMConfig

class LLMModel(Enum):
    class OpenAIRpaModels(Enum):
        GPT_3_5_TURBO = "gpt-3.5-turbo"
        GPT_4 = "gpt-4"
        GPT_4_0613 = "gpt-4-0613"
        GPT_4o = "GPT-4o"
        o1_PREVIEW = "o1-preview"
        o1_MINI = "o1-mini"
    class OpenaiApiModels(Enum):

        GPT_3_5_TURBO_API = "gpt-3.5-turbo-api"
        GPT_4_API = "gpt-4-api"
        GPT_4_0613_API = "gpt-4-0613-api"
        GPT_4o_API = "gpt-4o-api"
        o1_PREVIEW_API = "o1-preview-api"
        o1_MINI_API = "o1-mini-api"

    class MistralRpaModels(Enum):
        MISTRAL_SMALL = "mistral-small"
        MISTRAL_MEDIUM = "mistral-medium"
        MISTRAL_LARGE = "mistral-large"
    class MistralApiModels(Enum):
        MISTRAL_SMALL_API = "mistral-small-api"
        MISTRAL_MEDIUM_API = "mistral-medium-api"
        MISTRAL_LARGE_API = "mistral-large-api"

    class GroqRpaModels(Enum):
        GEMMA_2_9B_IT = "gemma2-9b-it"
        GEMMA_7B_IT = "gemma-7b-it"
        LLAMA_3_1_405B_REASONING = "llama-3-1-405b-reasoning"
        LLAMA_3_1_70B_VERSATILE = "llama-3-1-70b-versatile"
        LLAMA_3_1_8B_INSTANT = "llama-3-1-8b-instant"
        LLAMA3_70B_8192 = "llama3-70b-8192"
        LLAMA3_8B_8192 = "llama3-8b-8192"
        MIXTRAL_8X7B_32768 = "mixtral-8x7b-32768"
    class GroqApiModels(Enum):

        GEMMA_2_9B_IT_API = "gemma2-9b-it-api"
        GEMMA_7B_IT_API = "gemma-7b-it-api"
        LLAMA_3_1_405B_REASONING_API = "llama-3-1-405b-reasoning-api"
        LLAMA_3_1_70B_VERSATILE_API = "llama-3-1-70b-versatile-api"
        LLAMA_3_1_8B_INSTANT_API = "llama-3-1-8b-instant-api"
        LLAMA3_70B_8192_API = "llama3-70b-8192-api"
        LLAMA3_8B_8192_API = "llama3-8b-8192-api"
        MIXTRAL_8X7B_32768_API = "mixtral-8x7b-32768-api"

    class GeminiRpaModels(Enum):
        GEMINI_1_0_PRO = "gemini-1-0-pro"
        GEMINI_1_5_PRO = "gemini-1-5-pro"
        GEMINI_1_5_PRO_EXPERIMENTAL = "gemini-1-5-pro-experimental"
        GEMINI_1_5_FLASH = "gemini-1-5-flash"
        GEMMA_2_2B = "gemma-2-2b"
        GEMMA_2_9B = "gemma-2-9b"
        GEMMA_2_27B = "gemma-2-27b"

    class GeminiApiModels(Enum):
        GEMINI_1_0_PRO_API = "gemini-1-0-pro-api"
        GEMINI_1_5_PRO_API = "gemini-1-5-pro-api"
        GEMINI_1_5_PRO_EXPERIMENTAL_API = "gemini-1-5-pro-experimental-api"
        GEMINI_1_5_FLASH_API = "gemini-1-5-flash-api"
        GEMMA_2_2B_API = "gemma-2-2b-api"
        GEMMA_2_9B_API = "gemma-2-9b-api"
        GEMMA_2_27B_API = "gemma-2-27b-api"

    class ClaudeRpaModels(Enum):
        CLAUDE_3_HAIKU = "Claude3Haiku"
        CLAUDE_3_OPUS = "Claude3Opus"
        CLAUDE_3_5_SONNET = "Claude35Sonnet"
    class ClaudeApiModels(Enum):

        CLAUDE_3_HAIKU_API = "Claude3Haiku-api"
        CLAUDE_3_OPUS_API = "Claude3Opus-api"
        CLAUDE_3_5_SONNET_API = "Claude35Sonnet-api"

    class PerplexityRpaModels(Enum):
        LLAMA_3_1_SONAR_LARGE_128K_ONLINE = "llama-3-1-sonar-large-128k-online"
        LLAMA_3_1_SONAR_SMALL_128K_ONLINE = "llama-3-1-sonar-small-128k-online"
        LLAMA_3_1_SONAR_LARGE_128K_CHAT = "llama-3-1-sonar-large-128k-chat"
        LLAMA_3_1_SONAR_SMALL_128K_CHAT = "llama-3-1-sonar-small-128k-chat"
        LLAMA_3_1_8B_INSTRUCT = "llama-3-1-8b-instruct"
        LLAMA_3_1_70B_INSTRUCT = "llama-3-1-70b-instruct"
        GEMMA_2_27B_IT = "gemma-2-27b-it"
        NEMOTRON_4_340B_INSTRUCT = "nemotron-4-340b-instruct"
        MIXTRAL_8X7B_INSTRUCT = "mixtral-8x7b-instruct"
    class PerplexityApiModels(Enum):

        LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API = "llama-3-1-sonar-large-128k-online-api"
        LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API = "llama-3-1-sonar-small-128k-online-api"
        LLAMA_3_1_SONAR_LARGE_128K_CHAT_API = "llama-3-1-sonar-large-128k-chat-api"
        LLAMA_3_1_SONAR_SMALL_128K_CHAT_API = "llama-3-1-sonar-small-128k-chat-api"
        LLAMA_3_1_8B_INSTRUCT_API = "llama-3-1-8b-instruct-api"
        LLAMA_3_1_70B_INSTRUCT_API = "llama-3-1-70b-instruct-api"
        GEMMA_2_27B_IT_API = "gemma-2-27b-it-api"
        NEMOTRON_4_340B_INSTRUCT_API = "nemotron-4-340b-instruct-api"
        MIXTRAL_8X7B_INSTRUCT_API = "mixtral-8x7b-instruct-api"

    @property
    def default_config(self) -> LLMConfig:
        configs = {
            # OpenAI models
            self.OpenAIRpaModels.GPT_3_5_TURBO: LLMConfig(rate_limit=60, token_limit=4096),
            self.OpenAIRpaModels.GPT_4: LLMConfig(rate_limit=60, token_limit=8192),
            self.OpenAIRpaModels.GPT_4_0613: LLMConfig(rate_limit=60, token_limit=8192),
            self.OpenAIRpaModels.GPT_4o: LLMConfig(rate_limit=60, token_limit=8192),
            self.OpenAIRpaModels.o1_PREVIEW: LLMConfig(rate_limit=50, token_limit=16384),
            self.OpenAIRpaModels.o1_MINI: LLMConfig(rate_limit=60, token_limit=4096),
            self.OpenaiApiModels.GPT_4o_API: LLMConfig(rate_limit=40, token_limit=8192),
            self.OpenaiApiModels.o1_PREVIEW_API: LLMConfig(rate_limit=50, token_limit=16384),
            self.OpenaiApiModels.o1_MINI_API: LLMConfig(rate_limit=60, token_limit=4096),

            # Mistral models
            self.MistralRpaModels.MISTRAL_SMALL: LLMConfig(rate_limit=100, token_limit=32768),
            self.MistralRpaModels.MISTRAL_MEDIUM: LLMConfig(rate_limit=80, token_limit=32768),
            self.MistralRpaModels.MISTRAL_LARGE: LLMConfig(rate_limit=60, token_limit=32768),
            self.MistralApiModels.MISTRAL_SMALL_API: LLMConfig(rate_limit=100, token_limit=32768),
            self.MistralApiModels.MISTRAL_MEDIUM_API: LLMConfig(rate_limit=80, token_limit=32768),
            self.MistralApiModels.MISTRAL_LARGE_API: LLMConfig(rate_limit=60, token_limit=32768),

            # Groq models
            self.GroqRpaModels.GEMMA_2_9B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqRpaModels.GEMMA_7B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqRpaModels.LLAMA_3_1_405B_REASONING: LLMConfig(rate_limit=60, token_limit=4096),
            self.GroqRpaModels.LLAMA_3_1_70B_VERSATILE: LLMConfig(rate_limit=60, token_limit=4096),
            self.GroqRpaModels.LLAMA_3_1_8B_INSTANT: LLMConfig(rate_limit=60, token_limit=4096),
            self.GroqRpaModels.LLAMA3_70B_8192: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqRpaModels.LLAMA3_8B_8192: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqRpaModels.MIXTRAL_8X7B_32768: LLMConfig(rate_limit=60, token_limit=32768),
            self.GroqApiModels.GEMMA_2_9B_IT_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqApiModels.GEMMA_7B_IT_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqApiModels.LLAMA_3_1_405B_REASONING_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.GroqApiModels.LLAMA_3_1_70B_VERSATILE_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.GroqApiModels.LLAMA_3_1_8B_INSTANT_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.GroqApiModels.LLAMA3_70B_8192_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqApiModels.LLAMA3_8B_8192_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GroqApiModels.MIXTRAL_8X7B_32768_API: LLMConfig(rate_limit=60, token_limit=32768),

            # Gemini models
            self.GeminiRpaModels.GEMINI_1_0_PRO: LLMConfig(rate_limit=60, token_limit=30720),
            self.GeminiRpaModels.GEMINI_1_5_PRO: LLMConfig(rate_limit=20, token_limit=30720),
            self.GeminiRpaModels.GEMINI_1_5_PRO_EXPERIMENTAL: LLMConfig(rate_limit=30, token_limit=30720),
            self.GeminiRpaModels.GEMINI_1_5_FLASH: LLMConfig(rate_limit=60, token_limit=16384),
            self.GeminiRpaModels.GEMMA_2_2B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GeminiRpaModels.GEMMA_2_9B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GeminiRpaModels.GEMMA_2_27B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GeminiApiModels.GEMINI_1_0_PRO_API: LLMConfig(rate_limit=60, token_limit=30720),
            self.GeminiApiModels.GEMINI_1_5_PRO_API: LLMConfig(rate_limit=20, token_limit=30720),
            self.GeminiApiModels.GEMINI_1_5_PRO_EXPERIMENTAL_API: LLMConfig(rate_limit=30, token_limit=30720),
            self.GeminiApiModels.GEMINI_1_5_FLASH_API: LLMConfig(rate_limit=60, token_limit=16384),
            self.GeminiApiModels.GEMMA_2_2B_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GeminiApiModels.GEMMA_2_9B_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GeminiApiModels.GEMMA_2_27B_API: LLMConfig(rate_limit=60, token_limit=8192),

            # Claude models
            self.ClaudeRpaModels.CLAUDE_3_HAIKU: LLMConfig(rate_limit=60, token_limit=200000),
            self.ClaudeRpaModels.CLAUDE_3_OPUS: LLMConfig(rate_limit=40, token_limit=200000),
            self.ClaudeRpaModels.CLAUDE_3_5_SONNET: LLMConfig(rate_limit=50, token_limit=200000),
            self.ClaudeApiModels.CLAUDE_3_HAIKU_API: LLMConfig(rate_limit=60, token_limit=200000),
            self.ClaudeApiModels.CLAUDE_3_OPUS_API: LLMConfig(rate_limit=40, token_limit=200000),
            self.ClaudeApiModels.CLAUDE_3_5_SONNET_API: LLMConfig(rate_limit=50, token_limit=200000),

            # Perplexity models
            self.PerplexityRpaModels.LLAMA_3_1_SONAR_LARGE_128K_ONLINE: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityRpaModels.LLAMA_3_1_SONAR_SMALL_128K_ONLINE: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityRpaModels.LLAMA_3_1_SONAR_LARGE_128K_CHAT: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityRpaModels.LLAMA_3_1_SONAR_SMALL_128K_CHAT: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityRpaModels.LLAMA_3_1_8B_INSTRUCT: LLMConfig(rate_limit=60, token_limit=4096),
            self.PerplexityRpaModels.LLAMA_3_1_70B_INSTRUCT: LLMConfig(rate_limit=60, token_limit=4096),
            self.PerplexityRpaModels.GEMMA_2_27B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.PerplexityRpaModels.NEMOTRON_4_340B_INSTRUCT: LLMConfig(rate_limit=40, token_limit=32768),
            self.PerplexityRpaModels.MIXTRAL_8X7B_INSTRUCT: LLMConfig(rate_limit=60, token_limit=32768),
            self.PerplexityApiModels.LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityApiModels.LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityApiModels.LLAMA_3_1_SONAR_LARGE_128K_CHAT_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityApiModels.LLAMA_3_1_SONAR_SMALL_128K_CHAT_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.PerplexityApiModels.LLAMA_3_1_8B_INSTRUCT_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.PerplexityApiModels.LLAMA_3_1_70B_INSTRUCT_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.PerplexityApiModels.GEMMA_2_27B_IT_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.PerplexityApiModels.NEMOTRON_4_340B_INSTRUCT_API: LLMConfig(rate_limit=40, token_limit=32768),
            self.PerplexityApiModels.MIXTRAL_8X7B_INSTRUCT_API: LLMConfig(rate_limit=60, token_limit=32768),
        }
        return configs.get(self, LLMConfig())

    @property
    def is_api(self) -> bool:
        return self.value.endswith('-api')