from autobyteus.llm.models import LLMModel
from autobyteus.llm.api.ollama_llm import OllamaLLM
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from autobyteus.llm.ollama_provider_resolver import OllamaProviderResolver
from typing import TYPE_CHECKING, List
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
    CONNECTION_TIMEOUT = 5.0

    @staticmethod
    def _get_hosts() -> List[str]:
        """Gets Ollama hosts from env vars, supporting comma-separated list."""
        hosts_str = os.getenv('OLLAMA_HOSTS')
        if hosts_str:
            return [host.strip() for host in hosts_str.split(',')]

        return [OllamaModelProvider.DEFAULT_OLLAMA_HOST]

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate if the provided URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def get_models() -> List[LLMModel]:
        """
        Fetches models from all configured Ollama hosts and returns them as LLMModel objects.
        """
        hosts = OllamaModelProvider._get_hosts()
        all_models = []

        for host_url in hosts:
            if not OllamaModelProvider.is_valid_url(host_url):
                logger.error(f"Invalid Ollama host URL provided: '{host_url}', skipping.")
                continue
            
            logger.info(f"Discovering Ollama models from host: {host_url}")
            client = Client(host=host_url)
            
            try:
                response = client.list()
                models = response.get('models', [])
            except httpx.ConnectError:
                logger.warning(f"Could not connect to Ollama server at {host_url}. Please ensure it's running.")
                continue
            except Exception as e:
                logger.error(f"Failed to fetch models from {host_url}: {e}")
                continue

            for model_info in models:
                model_name = model_info.get('model')
                if not model_name:
                    continue

                try:
                    provider = OllamaProviderResolver.resolve(model_name)
                    
                    llm_model = LLMModel(
                        name=model_name,
                        value=model_name,
                        provider=provider,
                        llm_class=OllamaLLM,
                        canonical_name=model_name,
                        runtime=LLMRuntime.OLLAMA,
                        host_url=host_url,
                        default_config=LLMConfig(
                            pricing_config=TokenPricingConfig(0.0, 0.0) # Local models are free
                        )
                    )
                    all_models.append(llm_model)
                except Exception as e:
                    logger.warning(f"Failed to create LLMModel for '{model_name}' from host {host_url}: {e}")
        
        return all_models

    @staticmethod
    def discover_and_register():
        """
        Discovers all models from all configured Ollama hosts and registers them.
        """
        try:
            from autobyteus.llm.llm_factory import LLMFactory

            discovered_models = OllamaModelProvider.get_models()
            registered_count = 0

            for model in discovered_models:
                try:
                    LLMFactory.register_model(model)
                    registered_count += 1
                except Exception as e:
                    logger.warning(f"Failed to register Ollama model '{model.name}': {e}")
            
            if registered_count > 0:
                logger.info(f"Finished Ollama discovery. Total models registered: {registered_count}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during Ollama model discovery: {e}")
