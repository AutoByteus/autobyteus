from enum import Enum

class LLMRuntime(Enum):
    """
    Represents the serving layer or environment where an LLM model is executed.
    This is distinct from the LLMProvider, which is the creator of the model.
    """
    API = "api"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    AUTOBYTEUS = "autobyteus"
