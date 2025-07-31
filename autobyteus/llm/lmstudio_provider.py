from autobyteus.llm.models import LLMModel
from autobyteus.llm.api.lmstudio_llm import LMStudioLLM
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from typing import TYPE_CHECKING
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
        Discovers models from a local LM Studio instance and registers them with the LLMFactory.
        """
        try:
            from autobyteus.llm.llm_factory import LLMFactory
            
            lmstudio_host = os.getenv('LMSTUDIO_HOST', LMStudioModelProvider.DEFAULT_LMSTUDIO_HOST)
            
            if not LMStudioModelProvider.is_valid_url(lmstudio_host):
                logger.error(f"Invalid LM Studio host URL: {lmstudio_host}")
                return

            base_url = f"{lmstudio_host}/v1"
            
            # Use a dummy API key for initialization. LM Studio doesn't require one.
            client = OpenAI(base_url=base_url, api_key="lm-studio")

            try:
                response = client.models.list()
                models = response.data
            except APIConnectionError as e:
                logger.warning(
                    f"Could not connect to LM Studio server at {base_url}. "
                    "Please ensure LM Studio is running with the server started. "
                    f"Error: {e.__cause__}"
                )
                return
            except OpenAIError as e:
                logger.error(f"An error occurred while fetching models from LM Studio: {e}")
                return

            registered_count = 0
            for model_info in models:
                model_id = model_info.id
                if not model_id:
                    continue
                
                try:
                    llm_model = LLMModel(
                        name=model_id,
                        value=model_id,
                        provider=LLMProvider.LMSTUDIO,
                        llm_class=LMStudioLLM,
                        canonical_name=model_id,
                        default_config=LLMConfig(
                            rate_limit=None, # No rate limit for local models by default
                            token_limit=8192, # A reasonable default
                            pricing_config=TokenPricingConfig(0.0, 0.0) # Local models are free
                        )
                    )
                    LLMFactory.register_model(llm_model)
                    registered_count += 1
                except Exception as e:
                    logger.warning(f"Failed to register LM Studio model {model_id}: {str(e)}")

            if registered_count > 0:
                logger.info(f"Successfully registered {registered_count} LM Studio models from {lmstudio_host}")

        except Exception as e:
            logger.error(f"Unexpected error during LM Studio model discovery: {str(e)}")
