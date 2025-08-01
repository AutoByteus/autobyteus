import logging
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM
import os

logger = logging.getLogger(__name__)

class LMStudioLLM(OpenAICompatibleLLM):
    """
    LLM class for models served by a local LM Studio instance.

    This class communicates with an LM Studio server, which exposes an OpenAI-compatible API.
    It expects the LM Studio server to be running at the address specified by the `LMSTUDIO_HOST`
    environment variable, or at `http://localhost:1234` by default.

    Note: The LM Studio server does not require a real API key. A dummy key "lm-studio" is used
    by default. If you need to use a different key, you can set the `LMSTUDIO_API_KEY`
    environment variable.
    """
    DEFAULT_LMSTUDIO_HOST = 'http://localhost:1234'
    
    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        lmstudio_host = os.getenv('LMSTUDIO_HOST', self.DEFAULT_LMSTUDIO_HOST)
        base_url = f"{lmstudio_host}/v1"

        super().__init__(
            model=model,
            llm_config=llm_config,
            api_key_env_var="LMSTUDIO_API_KEY",
            base_url=base_url,
            api_key_default="lm-studio"
        )
        logger.info(f"LMStudioLLM initialized with model: {self.model.name} and base URL: {base_url}")

    async def cleanup(self):
        await super().cleanup()
