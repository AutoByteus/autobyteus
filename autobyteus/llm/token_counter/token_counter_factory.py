
from autobyteus.llm.token_counter.openai_token_counter import OpenAITokenCounter
from autobyteus.llm.token_counter.claude_token_counter import ClaudeTokenCounter
from autobyteus.llm.token_counter.mistral_token_counter import MistralTokenCounter
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider

def get_token_counter(model: LLMModel) -> BaseTokenCounter:
    """
    Return the appropriate token counter implementation based on the model.
    
    Args:
        model (LLMModel): The model enum indicating which LLM model is used.

    Returns:
        BaseTokenCounter: An instance of a token counter specific to the model.
    """
    if model.provider == LLMProvider.OPENAI:
        return OpenAITokenCounter(model)
    elif model.provider == LLMProvider.ANTHROPIC:
        return ClaudeTokenCounter(model)
    elif model.provider == LLMProvider.MISTRAL:
        return MistralTokenCounter(model)
    else:
        # For models that do not have a specialized counter, raise a NotImplementedError
        raise NotImplementedError(f"No token counter available for model {model.value}")
