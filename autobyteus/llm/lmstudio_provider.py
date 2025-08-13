from autobyteus.llm.models import LLMModel
from autobyteus.llm.api.lmstudio_llm import LMStudioLLM
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from typing import TYPE_CHECKING, List
import os
import logging
from openai import OpenAI, APIConnectionError, OpenAIError
from urllib.parse import urlparse

if TYPE_CHECKING:
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class LMStudioModelProvider:
    DEFAULT_LMSTUDIO_HOST = 'http://localhost:1234'

    @staticmethod
    def _get_hosts() -> List[str]:
        """Gets LM Studio hosts from env vars, supporting comma-separated list."""
        hosts_str = os.getenv('LMSTUDIO_HOSTS')
        if hosts_str:
            return [host.strip() for host in hosts_str.split(',')]
        
        legacy_host = os.getenv('LMSTUDIO_HOST') # For backward compatibility
        if legacy_host:
            return [legacy_host]
        
        return [LMStudioModelProvider.DEFAULT_LMSTUDIO_HOST]

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
        Discovers models from all configured LM Studio instances and registers them.
        """
        try:
            from autobyteus.llm.llm_factory import LLMFactory
            
            hosts = LMStudioModelProvider._get_hosts()
            total_registered_count = 0

            for host_url in hosts:
                if not LMStudioModelProvider.is_valid_url(host_url):
                    logger.error(f"Invalid LM Studio host URL: {host_url}, skipping.")
                    continue

                logger.info(f"Discovering LM Studio models from host: {host_url}")
                base_url = f"{host_url}/v1"
                client = OpenAI(base_url=base_url, api_key="lm-studio") # Dummy key

                try:
                    response = client.models.list()
                    models = response.data
                except APIConnectionError:
                    logger.warning(f"Could not connect to LM Studio at {host_url}. Please ensure the server is running.")
                    continue
                except OpenAIError as e:
                    logger.error(f"An error occurred fetching models from LM Studio at {host_url}: {e}")
                    continue

                host_registered_count = 0
                for model_info in models:
                    model_id = model_info.id
                    if not model_id:
                        continue
                    
                    try:
                        llm_model = LLMModel(
                            name=model_id,
                            value=model_id,
                            provider=LLMProvider.LMSTUDIO, # LMStudio is both provider and runtime
                            llm_class=LMStudioLLM,
                            canonical_name=model_id,
                            runtime=LLMRuntime.LMSTUDIO,
                            host_url=host_url,
                            default_config=LLMConfig(
                                pricing_config=TokenPricingConfig(0.0, 0.0) # Local models are free
                            )
                        )
                        LLMFactory.register_model(llm_model)
                        host_registered_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to register LM Studio model '{model_id}' from {host_url}: {e}")

                if host_registered_count > 0:
                    logger.info(f"Registered {host_registered_count} models from LM Studio host {host_url}")
                total_registered_count += host_registered_count

            if total_registered_count > 0:
                logger.info(f"Finished LM Studio discovery. Total models registered: {total_registered_count}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during LM Studio model discovery: {e}")
