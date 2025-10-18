from autobyteus.llm.providers import LLMProvider
import logging

logger = logging.getLogger(__name__)

class LocalModelProviderResolver:
    """
    A utility class to resolve the correct LLMProvider for local models
    based on keywords in their names. This helps attribute models to their
    original creators.
    """
    
    KEYWORD_PROVIDER_MAP = [
        (['gpt'], LLMProvider.OPENAI),
        (['claude'], LLMProvider.ANTHROPIC),
        (['gemma', 'gemini'], LLMProvider.GEMINI),
        (['llama'], LLMProvider.GROQ), # Using GROQ as it's a prominent Llama provider
        (['mistral', 'mixtral'], LLMProvider.MISTRAL),
        (['deepseek'], LLMProvider.DEEPSEEK),
        (['qwen'], LLMProvider.QWEN),
        (['glm'], LLMProvider.ZHIPU),
        (['grok'], LLMProvider.GROK),
        (['kimi'], LLMProvider.KIMI),
    ]

    @staticmethod
    def resolve(model_name: str) -> LLMProvider:
        """
        Resolves the LLMProvider for a given local model name (e.g., from a file path).
        It checks for keywords and defaults to a generic provider if none match.

        Args:
            model_name (str): The name of the model (e.g., 'Llama-3-8B-Instruct.gguf').

        Returns:
            LLMProvider: The resolved provider for the model.
        """
        lower_model_name = model_name.lower()
        
        for keywords, provider in LocalModelProviderResolver.KEYWORD_PROVIDER_MAP:
            for keyword in keywords:
                if keyword in lower_model_name:
                    logger.debug(f"Resolved provider for model '{model_name}' to '{provider.name}' based on keyword '{keyword}'.")
                    return provider
                    
        logger.debug(f"Model '{model_name}' did not match any specific provider keywords. Defaulting to OLLAMA as a generic local provider.")
        return LLMProvider.OLLAMA # Default for unknown local models
