from autobyteus.llm.providers import LLMProvider
import logging

logger = logging.getLogger(__name__)

class OllamaProviderResolver:
    """
    A utility class to resolve the correct LLMProvider for Ollama models
    based on keywords in their names. This helps attribute models to their
    original creators (e.g., Google for 'gemma').
    """
    
    # A mapping from keywords to providers. The list is ordered to handle
    # potential overlaps, though current keywords are distinct.
    KEYWORD_PROVIDER_MAP = [
        (['gemma', 'gemini'], LLMProvider.GEMINI),
        (['llama'], LLMProvider.GROQ),
        (['mistral'], LLMProvider.MISTRAL),
        (['deepseek'], LLMProvider.DEEPSEEK),
    ]

    @staticmethod
    def resolve(model_name: str) -> LLMProvider:
        """
        Resolves the LLMProvider for a given model name from Ollama.
        It checks for keywords in the model name and returns the corresponding
        provider. If no specific provider is found, it defaults to OLLAMA.

        Args:
            model_name (str): The name of the model discovered from Ollama (e.g., 'gemma:7b').

        Returns:
            LLMProvider: The resolved provider for the model.
        """
        lower_model_name = model_name.lower()
        
        for keywords, provider in OllamaProviderResolver.KEYWORD_PROVIDER_MAP:
            for keyword in keywords:
                if keyword in lower_model_name:
                    logger.debug(f"Resolved provider for model '{model_name}' to '{provider.name}' based on keyword '{keyword}'.")
                    return provider
                    
        logger.debug(f"Model '{model_name}' did not match any specific provider keywords. Defaulting to OLLAMA provider.")
        return LLMProvider.OLLAMA
