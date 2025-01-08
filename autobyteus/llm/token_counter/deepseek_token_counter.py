from typing import TYPE_CHECKING
from autobyteus.llm.token_counter.openai_token_counter import OpenAITokenCounter
from autobyteus.llm.models import LLMModel

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

class DeepSeekTokenCounter(OpenAITokenCounter):
    """
    Token counter for DeepSeek models. Uses the same token counting implementation as OpenAI.
    
    This implementation inherits from OpenAITokenCounter as DeepSeek uses the same tokenization
    approach as OpenAI's models.
    """
    
    def __init__(self, model: LLMModel, llm: 'BaseLLM' = None):
        """
        Initialize the DeepSeek token counter.
        
        Args:
            model (LLMModel): The DeepSeek model to count tokens for.
            llm (BaseLLM, optional): The LLM instance. Defaults to None.
        """
        super().__init__(model, llm)