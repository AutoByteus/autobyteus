from enum import Enum

class LLMProvider(Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    MISTRAL = "MISTRAL"
    GEMINI = "GEMINI"
    OLLAMA = "OLLAMA"
    DEEPSEEK = "DEEPSEEK"
    GROK = "GROK"
    AUTOBYTEUS = "AUTOBYTEUS"
    KIMI = "KIMI"
    QWEN = "QWEN"
    LMSTUDIO = "LMSTUDIO"
    ZHIPU = "ZHIPU"
    BAIDU = "BAIDU"
