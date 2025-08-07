import logging
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM
import os

logger = logging.getLogger(__name__)

class LMStudioLLM(OpenAICompatibleLLM):
    """
    LLM class for models served by a local LM Studio instance.
    This class is now decoupled from environment variables and receives its connection
    details from the LLMModel object.
    """
    
    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        if not model.host_url:
            raise ValueError("LMStudioLLM requires a host_url to be set in its LLMModel object.")

        base_url = f"{model.host_url}/v1"

        # The API key is often not needed for LM Studio, but we allow it to be set via env var.
        # It defaults to a dummy value if not set.
        super().__init__(
            model=model,
            llm_config=llm_config,
            api_key_env_var="LMSTUDIO_API_KEY",
            base_url=base_url,
            api_key_default="lm-studio" # Dummy key for LM Studio
        )
        logger.info(f"LMStudioLLM initialized for model '{model.model_identifier}' with base URL: {base_url}")

    async def cleanup(self):
        await super().cleanup()
