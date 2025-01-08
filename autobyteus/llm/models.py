
from enum import Enum
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.providers import LLMProvider


class LLMModel(Enum):
    # Existing models...
    NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API = (
        "nvidia/llama-3.1-nemotron-70b-instruct"
    )

    # OpenAI models
    GPT_4o_API = "gpt-4o"
    o1_API = "o1"
    o1_MINI_API = "o1-mini"
    CHATGPT_4O_LATEST_API = "chatgpt-4o-latest"
    GPT_3_5_TURBO_API = "gpt-3.5-turbo"

    # Mistral models
    MISTRAL_SMALL_API = "mistral-small-latest"
    MISTRAL_MEDIUM_API = "mistral-medium"
    MISTRAL_LARGE_API = "mistral-large-latest"

    # Groq models
    GEMMA_2_9B_IT_API = "gemma2-9b-it"
    GEMMA_7B_IT_API = "gemma-7b-it"
    LLAMA_3_1_405B_REASONING_API = "llama-3-1-405b-reasoning"
    LLAMA_3_1_70B_VERSATILE_API = "llama-3-1-70b-versatile"
    LLAMA_3_1_8B_INSTANT_API = "llama-3-1-8b-instant"
    LLAMA3_70B_8192_API = "llama3-70b-8192"
    LLAMA3_8B_8192_API = "llama3-8b-8192"
    MIXTRAL_8X7B_32768_API = "mixtral-8x7b-32768"

    # Gemini models
    GEMINI_1_0_PRO_API = "gemini-1-0-pro"
    GEMINI_1_5_PRO_API = "gemini-1-5-pro"
    GEMINI_1_5_PRO_EXPERIMENTAL_API = "gemini-1-5-pro-experimental"
    GEMINI_1_5_FLASH_API = "gemini-1-5-flash"
    GEMMA_2_2B_API = "gemma-2-2b"
    GEMMA_2_9B_API = "gemma-2-9b"
    GEMMA_2_27B_API = "gemma-2-27b"

    # Claude models
    CLAUDE_3_OPUS_API = "claude-3-opus-20240229"
    CLAUDE_3_SONNET_API = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU_API = "claude-3-haiku-20240307"
    CLAUDE_3_5_SONNET_API = "claude-3-5-sonnet-20240620"
    BEDROCK_CLAUDE_3_5_SONNET_API = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    # Perplexity models
    LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API = "llama-3-1-sonar-large-128k-online"
    LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API = "llama-3-1-sonar-small-128k-online"
    LLAMA_3_1_SONAR_LARGE_128K_CHAT_API = "llama-3-1-sonar-large-128k-chat"
    LLAMA_3_1_SONAR_SMALL_128K_CHAT_API = "llama-3-1-sonar-small-128k-chat"
    LLAMA_3_1_8B_INSTRUCT_API = "llama-3-1-8b-instruct"
    LLAMA_3_1_70B_INSTRUCT_API = "llama-3-1-70b-instruct"
    GEMMA_2_27B_IT_API = "gemma-2-27b-it"
    NEMOTRON_4_340B_INSTRUCT_API = "nemotron-4-340b-instruct"
    MIXTRAL_8X7B_INSTRUCT_API = "mixtral-8x7b-instruct"

    # Ollama models
    OLLAMA_LLAMA_3_2 = "llama3.2"

    # DeepSeek models
    DEEPSEEK_CHAT_API = "deepseek-chat"

    @property
    def provider(self) -> LLMProvider:
        provider_mapping = {
            # Existing mappings...
            self.GPT_4o_API: LLMProvider.OPENAI,
            self.o1_API: LLMProvider.OPENAI,
            self.o1_MINI_API: LLMProvider.OPENAI,
            self.CHATGPT_4O_LATEST_API: LLMProvider.OPENAI,
            self.GPT_3_5_TURBO_API: LLMProvider.OPENAI,
            self.MISTRAL_SMALL_API: LLMProvider.MISTRAL,
            self.MISTRAL_MEDIUM_API: LLMProvider.MISTRAL,
            self.MISTRAL_LARGE_API: LLMProvider.MISTRAL,
            self.GEMMA_2_9B_IT_API: LLMProvider.GROQ,
            self.GEMMA_7B_IT_API: LLMProvider.GROQ,
            self.LLAMA_3_1_405B_REASONING_API: LLMProvider.GROQ,
            self.LLAMA_3_1_70B_VERSATILE_API: LLMProvider.GROQ,
            self.LLAMA_3_1_8B_INSTANT_API: LLMProvider.GROQ,
            self.LLAMA3_70B_8192_API: LLMProvider.GROQ,
            self.LLAMA3_8B_8192_API: LLMProvider.GROQ,
            self.MIXTRAL_8X7B_32768_API: LLMProvider.GROQ,
            self.GEMINI_1_0_PRO_API: LLMProvider.GEMINI,
            self.GEMINI_1_5_PRO_API: LLMProvider.GEMINI,
            self.GEMINI_1_5_PRO_EXPERIMENTAL_API: LLMProvider.GEMINI,
            self.GEMINI_1_5_FLASH_API: LLMProvider.GEMINI,
            self.GEMMA_2_2B_API: LLMProvider.GEMINI,
            self.GEMMA_2_9B_API: LLMProvider.GEMINI,
            self.GEMMA_2_27B_API: LLMProvider.GEMINI,
            self.CLAUDE_3_OPUS_API: LLMProvider.ANTHROPIC,
            self.CLAUDE_3_SONNET_API: LLMProvider.ANTHROPIC,
            self.CLAUDE_3_HAIKU_API: LLMProvider.ANTHROPIC,
            self.CLAUDE_3_5_SONNET_API: LLMProvider.ANTHROPIC,
            self.BEDROCK_CLAUDE_3_5_SONNET_API: LLMProvider.ANTHROPIC,
            self.NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API: LLMProvider.NVIDIA,
            self.LLAMA_3_1_SONAR_LARGE_128K_ONLINE_API: LLMProvider.PERPLEXITY,
            self.LLAMA_3_1_SONAR_SMALL_128K_ONLINE_API: LLMProvider.PERPLEXITY,
            self.LLAMA_3_1_SONAR_LARGE_128K_CHAT_API: LLMProvider.PERPLEXITY,
            self.LLAMA_3_1_SONAR_SMALL_128K_CHAT_API: LLMProvider.PERPLEXITY,
            self.LLAMA_3_1_8B_INSTRUCT_API: LLMProvider.PERPLEXITY,
            self.LLAMA_3_1_70B_INSTRUCT_API: LLMProvider.PERPLEXITY,
            self.GEMMA_2_27B_IT_API: LLMProvider.PERPLEXITY,
            self.NEMOTRON_4_340B_INSTRUCT_API: LLMProvider.PERPLEXITY,
            self.MIXTRAL_8X7B_INSTRUCT_API: LLMProvider.PERPLEXITY,
            self.OLLAMA_LLAMA_3_2: LLMProvider.OLLAMA,
            # Add DeepSeek mapping
            self.DEEPSEEK_CHAT_API: LLMProvider.DEEPSEEK,
        }
        return provider_mapping[self]

    @property
    def default_config(self) -> LLMConfig:
        configs = {
            # Existing configs...
            self.NVIDIA_LLAMA_3_1_NEMOTRON_70B_INSTRUCT_API: LLMConfig(
                rate_limit=60, token_limit=32768
            ),
            self.GPT_4o_API: LLMConfig(rate_limit=40, token_limit=8192),
            # ... [other existing configs]
            self.OLLAMA_LLAMA_3_2: LLMConfig(rate_limit=60, token_limit=8192),
            # Add DeepSeek config
            self.DEEPSEEK_CHAT_API: LLMConfig(rate_limit=60, token_limit=8000),
        }
        return configs.get(self, LLMConfig())

    @classmethod
    def from_name(cls, name: str) -> "LLMModel":
        try:
            return cls[name]
        except KeyError:
            raise ValueError(f"Invalid LLMModel name: {name}")
