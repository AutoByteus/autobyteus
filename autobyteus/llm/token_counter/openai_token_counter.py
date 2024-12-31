
import tiktoken
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel

class OpenAITokenCounter(BaseTokenCounter):
    """
    A token counter implementation for OpenAI models using tiktoken.
    """
    def __init__(self, model: LLMModel):
        super().__init__(model)
        try:
            self.encoding = tiktoken.encoding_for_model(model.value)
        except Exception:
            # fallback if model_name is not recognized
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.encoding.encode(text))
