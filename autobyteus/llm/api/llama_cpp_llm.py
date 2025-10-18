import logging
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM

logger = logging.getLogger(__name__)

class LlamaCppLLM(OpenAICompatibleLLM):
    """
    LLM class for models served by a local llama.cpp server instance.
    This class communicates with an OpenAI-compatible API.
    """
    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        if not model.host_url:
            raise ValueError("LlamaCppLLM requires a host_url to be set in its LLMModel object.")

        base_url = f"{model.host_url}/v1"

        super().__init__(
            model=model,
            llm_config=llm_config,
            api_key_env_var="LLAMACPP_API_KEY", # Not used, but required by parent
            base_url=base_url,
            api_key_default="local-key" # Dummy key
        )
        logger.info(f"LlamaCppLLM initialized for model '{model.model_identifier}' with base URL: {base_url}")
