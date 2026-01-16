from typing import TYPE_CHECKING, Optional
import logging

from autobyteus.llm.token_counter.openai_token_counter import OpenAITokenCounter
from autobyteus.llm.token_counter.claude_token_counter import ClaudeTokenCounter
from autobyteus.llm.token_counter.mistral_token_counter import MistralTokenCounter
from autobyteus.llm.token_counter.deepseek_token_counter import DeepSeekTokenCounter
from autobyteus.llm.token_counter.kimi_token_counter import KimiTokenCounter
from autobyteus.llm.token_counter.zhipu_token_counter import ZhipuTokenCounter
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider

if TYPE_CHECKING:
    from autobyteus.llm.base_llm import BaseLLM

logger = logging.getLogger(__name__)

def get_token_counter(model: LLMModel, llm: 'BaseLLM') -> Optional[BaseTokenCounter]:
    """
    Return the appropriate token counter implementation based on the model.
    
    Args:
        model (LLMModel): The model enum indicating which LLM model is used.
        llm (BaseLLM): The LLM instance.

    Returns:
        Optional[BaseTokenCounter]: An instance of a token counter specific to the model,
            or None if no token counter is available for the provider.
    """
    if model.provider == LLMProvider.OPENAI:
        return OpenAITokenCounter(model, llm)
    elif model.provider == LLMProvider.ANTHROPIC:
        return OpenAITokenCounter(model, llm)
    elif model.provider == LLMProvider.MISTRAL:
        return MistralTokenCounter(model, llm)
    elif model.provider == LLMProvider.DEEPSEEK:
        return DeepSeekTokenCounter(model, llm)
    elif model.provider == LLMProvider.GROK:
        return DeepSeekTokenCounter(model, llm)
    elif model.provider == LLMProvider.KIMI:
        return KimiTokenCounter(model, llm)
    elif model.provider == LLMProvider.QWEN:
        return OpenAITokenCounter(model, llm)
    elif model.provider == LLMProvider.OLLAMA:
        return OpenAITokenCounter(model, llm)
    elif model.provider == LLMProvider.LMSTUDIO:
        return OpenAITokenCounter(model, llm)
    elif model.provider == LLMProvider.GEMINI:
        return OpenAITokenCounter(model, llm)
    elif model.provider == LLMProvider.ZHIPU:
        return ZhipuTokenCounter(model, llm)
    else:
        # For providers without a specialized counter, return None and log a warning
        logger.info(f"No token counter available for provider {model.provider.value}. Token usage tracking will be disabled.")
        return None

