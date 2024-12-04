from enum import Enum

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    GROQ = "groq"
    GOOGLE = "google"
    NVIDIA = "nvidia"
    PERPLEXITY = "perplexity"