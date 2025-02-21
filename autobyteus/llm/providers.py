from enum import Enum

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    GROQ = "groq"
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    PERPLEXITY = "perplexity"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    GROK = "grok"
    AUTOBYTEUS = "autobyteus"
