# file: autobyteus/llm/LLMFactory.py
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM

class LLMFactory:
    @staticmethod
    def create_llm(model: LLMModel) -> BaseLLM:
        raise NotImplementedError("This method should be overridden by subclasses.")
