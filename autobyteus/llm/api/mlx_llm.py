import logging
import sys
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM

logger = logging.getLogger(__name__)

class MlxLLM(OpenAICompatibleLLM):
    """
    LLM class for models served by a local mlx_lm.server instance on Apple Silicon.
    This class communicates with an OpenAI-compatible API.
    """
    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        if sys.platform != "darwin":
            raise RuntimeError("MlxLLM can only be used on macOS (Apple Silicon).")
            
        if not model.host_url:
            raise ValueError("MlxLLM requires a host_url to be set in its LLMModel object.")

        base_url = f"{model.host_url}/v1"

        super().__init__(
            model=model,
            llm_config=llm_config,
            api_key_env_var="MLX_API_KEY", # Not used, but required by parent
            base_url=base_url,
            api_key_default="local-key" # Dummy key
        )
        logger.info(f"MlxLLM initialized for model '{model.model_identifier}' with base URL: {base_url}")
