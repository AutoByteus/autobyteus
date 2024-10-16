from enum import Enum
from autobyteus.llm.utils.llm_config import LLMConfig

class LLMModel(Enum):
    # ChatGPT models
    GPT_4o = "GPT-4o"
    o1_PREVIEW = "o1-preview"
    o1_MINI = "o1-mini"

    GPT_4o_API = "gpt-4o"
    o1_PREVIEW_API = "o1-preview"
    o1_MINI_API = "o1-mini"
    CHATGPT_4O_LATEST_API = "chatgpt-4o-latest"

    # Mistral models
    MISTRAL_SMALL = "mistral-small"
    MISTRAL_MEDIUM = "mistral-medium"
    MISTRAL_LARGE = "mistral-large"
    MISTRAL_SMALL_API = "mistral-small-api"
    MISTRAL_MEDIUM_API = "mistral-medium-api"
    MISTRAL_LARGE_API = "mistral-large-latest"

    # Groq models
    GEMMA_2_9B_IT = "gemma2-9b-it"
    GEMMA_7B_IT = "gemma-7b-it"
    LLAMA_3_1_405B_REASONING = "llama-3-1-405b-reasoning"
    LLAMA_3_1_70B_VERSATILE = "llama-3-1-70b-versatile"
    LLAMA_3_1_8B_INSTANT = "llama-3-1-8b-instant"
    LLAMA3_70B_8192 = "llama3-70b-8192"
    LLAMA3_8B_8192 = "llama3-8b-8192"
    MIXTRAL_8X7B_32768 = "mixtral-8x7b-32768"
    GEMMA_2_9B_IT_API = "gemma2-9b-it-api"
    GEMMA_7B_IT_API = "gemma-7b-it-api"
    LLAMA_3_1_405B_REASONING_API = "llama-3-1-405b-reasoning-api"
    LLAMA_3_1_70B_VERSATILE_API = "llama-3-1-70b-versatile-api"
    LLAMA_3_1_8B_INSTANT_API = "llama-3-1-8b-instant-api"
    LLAMA3_70B_8192_API = "llama3-70b-8192-api"
    LLAMA3_8B_8192_API = "llama3-8b-8192-api"
    MIXTRAL_8X7B_32768_API = "mixtral-8x7b-32768-api"

    # Gemini models
    GEMINI_1_0_PRO = "gemini-1-0-pro"
    GEMINI_1_5_PRO = "gemini-1-5-pro"
    GEMINI_1_5_PRO_EXPERIMENTAL = "gemini-1-5-pro-experimental"
    GEMINI_1_5_FLASH = "gemini-1-5-flash"
    GEMMA_2_2B = "gemma-2-2b"
    GEMMA_2_9B = "gemma-2-9b"
    GEMMA_2_27B = "gemma-2-27b"
    GEMINI_1_0_PRO_API = "gemini-1-0-pro-api"
    GEMINI_1_5_PRO_API = "gemini-1-5-pro-api"
    GEMINI_1_5_PRO_EXPERIMENTAL_API = "gemini-1-5-pro-experimental-api"
    GEMINI_1_5_FLASH_API = "gemini-1.5-flash"
    GEMMA_2_2B_API = "gemma-2-2b-api"
    GEMMA_2_9B_API = "gemma-2-9b-api"
    GEMMA_2_27B_API = "gemma-2-27b-api"

    # Claude models
    CLAUDE_3_HAIKU = "Claude3Haiku"
    CLAUDE_3_OPUS = "Claude3Opus"
    CLAUDE_3_5_SONNET = "Claude35Sonnet"
    CLAUDE_3_HAIKU_API = "Claude3Haiku-api"
    CLAUDE_3_OPUS_API = "Claude3Opus-api"
    CLAUDE_3_5_SONNET_API = "Claude35Sonnet-api"
    CLAUDE_3_5_SONNET_LATEST_API = "claude-3-5-sonnet-20240620"
    BEDROCK_CLAUDE_3_5_SONNET_API = "anthropic.claude-3-5-sonnet-20240620-v1:0"

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
            # ChatGPT models
            self.GPT_4o: LLMConfig(rate_limit=40, token_limit=8192),
            self.o1_PREVIEW: LLMConfig(rate_limit=50, token_limit=16384),  # Adjust these values
            self.o1_MINI: LLMConfig(rate_limit=60, token_limit=4096),  # Adjust these values
            self.GPT_4o_API: LLMConfig(rate_limit=40, token_limit=8192),
            self.o1_PREVIEW_API: LLMConfig(rate_limit=50, token_limit=16384),  # Adjust these values
            self.o1_MINI_API: LLMConfig(rate_limit=60, token_limit=4096),  # Adjust these values
            self.CHATGPT_4O_LATEST_API: LLMConfig(rate_limit=40, token_limit=8192),

            # Mistral models
            self.MISTRAL_SMALL: LLMConfig(rate_limit=100, token_limit=32768),
            self.MISTRAL_MEDIUM: LLMConfig(rate_limit=80, token_limit=32768),
            self.MISTRAL_LARGE: LLMConfig(rate_limit=60, token_limit=32768),
            self.MISTRAL_SMALL_API: LLMConfig(rate_limit=100, token_limit=32768),
            self.MISTRAL_MEDIUM_API: LLMConfig(rate_limit=80, token_limit=32768),
            self.MISTRAL_LARGE_API: LLMConfig(rate_limit=60, token_limit=32768),

            # Groq models
            self.GEMMA_2_9B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_7B_IT: LLMConfig(rate_limit=60, token_limit=8192),
            self.LLAMA_3_1_405B_REASONING: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_70B_VERSATILE: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_8B_INSTANT: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA3_70B_8192: LLMConfig(rate_limit=60, token_limit=8192),
            self.LLAMA3_8B_8192: LLMConfig(rate_limit=60, token_limit=8192),
            self.MIXTRAL_8X7B_32768: LLMConfig(rate_limit=60, token_limit=32768),
            self.GEMMA_2_9B_IT_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_7B_IT_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.LLAMA_3_1_405B_REASONING_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_70B_VERSATILE_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_8B_INSTANT_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA3_70B_8192_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.LLAMA3_8B_8192_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.MIXTRAL_8X7B_32768_API: LLMConfig(rate_limit=60, token_limit=32768),

            # Gemini models
            self.GEMINI_1_0_PRO: LLMConfig(rate_limit=60, token_limit=30720),
            self.GEMINI_1_5_PRO: LLMConfig(rate_limit=20, token_limit=30720),
            self.GEMINI_1_5_PRO_EXPERIMENTAL: LLMConfig(rate_limit=30, token_limit=30720),
            self.GEMINI_1_5_FLASH: LLMConfig(rate_limit=60, token_limit=16384),
            self.GEMMA_2_2B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_2_9B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_2_27B: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMINI_1_0_PRO_API: LLMConfig(rate_limit=60, token_limit=30720),
            self.GEMINI_1_5_PRO_API: LLMConfig(rate_limit=20, token_limit=30720),
            self.GEMINI_1_5_PRO_EXPERIMENTAL_API: LLMConfig(rate_limit=30, token_limit=30720),
            self.GEMINI_1_5_FLASH_API: LLMConfig(rate_limit=60, token_limit=16384),
            self.GEMMA_2_2B_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_2_9B_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.GEMMA_2_27B_API: LLMConfig(rate_limit=60, token_limit=8192),

            # Claude models
            self.CLAUDE_3_HAIKU: LLMConfig(rate_limit=60, token_limit=200000),
            self.CLAUDE_3_OPUS: LLMConfig(rate_limit=40, token_limit=200000),
            self.CLAUDE_3_5_SONNET: LLMConfig(rate_limit=50, token_limit=200000),
            self.CLAUDE_3_HAIKU_API: LLMConfig(rate_limit=60, token_limit=200000),
            self.CLAUDE_3_OPUS_API: LLMConfig(rate_limit=40, token_limit=200000),
            self.CLAUDE_3_5_SONNET_API: LLMConfig(rate_limit=50, token_limit=200000),
            self.CLAUDE_3_5_SONNET_LATEST_API: LLMConfig(rate_limit=50, token_limit=200000),
            self.BEDROCK_CLAUDE_3_5_SONNET_API: LLMConfig(rate_limit=50, token_limit=200000),

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
            self.LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_SONAR_LARGE_128K_CHAT_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_SONAR_SMALL_128K_CHAT_API: LLMConfig(rate_limit=60, token_limit=128000),
            self.LLAMA_3_1_8B_INSTRUCT_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.LLAMA_3_1_70B_INSTRUCT_API: LLMConfig(rate_limit=60, token_limit=4096),
            self.GEMMA_2_27B_IT_API: LLMConfig(rate_limit=60, token_limit=8192),
            self.NEMOTRON_4_340B_INSTRUCT_API: LLMConfig(rate_limit=40, token_limit=32768),
            self.MIXTRAL_8X7B_INSTRUCT_API: LLMConfig(rate_limit=60, token_limit=32768),
        }
        return configs.get(self, LLMConfig())
    @property
    def is_api(self) -> bool:
        return self.name.endswith('_API')