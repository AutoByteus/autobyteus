from typing import TYPE_CHECKING
from autobyteus.llm.token_counter.openai_token_counter import OpenAITokenCounter
from autobyteus.llm.models import LLMModel

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

class ZhipuTokenCounter(OpenAITokenCounter):
    """
    Token counter for Zhipu models. Uses the same token counting implementation as OpenAI.
    
    This implementation inherits from OpenAITokenCounter as Zhipu uses a similar tokenization
    approach as OpenAI's models.
    """
    
    def __init__(self, model: LLMModel, llm: 'BaseLLM' = None):
        """
        Initialize the Zhipu token counter.
        
        Args:
            model (LLMModel): The Zhipu model to count tokens for.
            llm (BaseLLM, optional): The LLM instance. Defaults to None.
        """
        super().__init__(model, llm)
