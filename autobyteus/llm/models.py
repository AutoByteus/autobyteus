from enum import Enum

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
    GEMINI = "gemini"
    
    # Claude models
    CLAUDE_3_HAIKU = "Claude3Haiku"
    CLAUDE_3_OPUS = "Claude3Opus"
    CLAUDE_3_5_SONNET = "Claude35Sonnet"