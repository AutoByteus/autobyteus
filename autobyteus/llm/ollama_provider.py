from autobyteus.llm.models import LLMModel
from autobyteus.llm.api.ollama_llm import OllamaLLM
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from typing import TYPE_CHECKING
import os
import logging
from ollama import Client
import httpx
from urllib.parse import urlparse

if TYPE_CHECKING:
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class OllamaModelProvider:
    DEFAULT_OLLAMA_HOST = 'http://localhost:11434'
    CONNECTION_TIMEOUT = 5.0  # 5 seconds timeout

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate if the provided URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def discover_and_register():
        """
        Discovers all models supported by Ollama using a synchronous Client
        and registers them directly using LLMFactory.
        
        Handles various connection and operational errors gracefully to prevent
        application crashes when Ollama is unavailable.
        """
        try:
            from autobyteus.llm.llm_factory import LLMFactory  # Local import to avoid circular dependency
            
            ollama_host = os.getenv('OLLAMA_HOST', OllamaLLM.DEFAULT_OLLAMA_HOST)
            
            if not OllamaModelProvider.is_valid_url(ollama_host):
                logger.error(f"Invalid Ollama host URL: {ollama_host}")
                return
            
            client = Client(host=ollama_host)
            
            try:
                response = client.list()
            except httpx.ConnectError as e:
                logger.warning(f"Could not connect to Ollama server at {ollama_host}. "
                             f"Please ensure Ollama is running. Error: {str(e)}")
                return
            except httpx.TimeoutException as e:
                logger.warning(f"Connection to Ollama server timed out. "
                             f"Please check if the server is responsive. Error: {str(e)}")
                return
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error occurred while connecting to Ollama: {str(e)}")
                return
            
            try:
                models = response['models']
            except (KeyError, TypeError) as e:
                logger.error(f"Unexpected response format from Ollama server: {str(e)}")
                return
            
            registered_count = 0
            for model_info in models:
                try:
                    model_name = model_info.get('model')
                    if not model_name:
                        continue
                        
                    llm_model = LLMModel(
                        name=model_name,
                        value=model_name,
                        provider=LLMProvider.OLLAMA,
                        llm_class=OllamaLLM,
                        default_config=LLMConfig(
                            rate_limit=60,
                            token_limit=8192,
                            pricing_config=TokenPricingConfig(0.0, 0.0)
                        )
                    )
                    LLMFactory.register_model(llm_model)
                    registered_count += 1
                except Exception as e:
                    logger.warning(f"Failed to register model {model_name}: {str(e)}")
                    continue
                    
            logger.info(f"Successfully registered {registered_count} Ollama models from {ollama_host}")
            
        except Exception as e:
            logger.error(f"Unexpected error during Ollama model discovery: {str(e)}")
            # Don't re-raise the exception to prevent application crash
