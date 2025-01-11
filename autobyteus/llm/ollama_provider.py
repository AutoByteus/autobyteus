from autobyteus.llm.models import LLMModel
from autobyteus.llm.api.ollama_llm import OllamaLLM
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from typing import TYPE_CHECKING
import os
import logging
from ollama import Client

if TYPE_CHECKING:
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class OllamaModelProvider:
    DEFAULT_OLLAMA_HOST = 'http://localhost:11434'

    @staticmethod
    def discover_and_register():
        """
        Discovers all models supported by Ollama using a synchronous Client
        and registers them directly using LLMFactory.register_model.
        """
        try:
            from autobyteus.llm.llm_factory import LLMFactory  # Local import to avoid circular dependency
            ollama_host = os.getenv('OLLAMA_HOST', OllamaLLM.DEFAULT_OLLAMA_HOST)
            client = Client(host=ollama_host)

            response = client.list()
            models = response['models']

            for model_info in models:
                llm_model = LLMModel(
                    name=model_info['name'],
                    value=model_info['model'],
                    provider=LLMProvider.OLLAMA,
                    llm_class=OllamaLLM,
                    default_config=LLMConfig(
                        rate_limit=60,
                        token_limit=8192,
                        pricing_config=TokenPricingConfig(0.0, 0.0)
                    )
                )
                LLMFactory.register_model(llm_model)
            logger.info(f"Discovered and registered {len(models)} Ollama models from host {ollama_host}.")
        except KeyError as e:
            logger.error(f"Missing expected key in model information: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to discover Ollama models: {e}")
            raise
