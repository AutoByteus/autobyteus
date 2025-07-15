import logging
from typing import Optional
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM

logger = logging.getLogger(__name__)

class KimiLLM(OpenAICompatibleLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        # Provide defaults if not specified
        if model is None:
            # Setting a default Kimi model from the factory ones
            model = LLMModel['kimi-latest']
        if llm_config is None:
            llm_config = LLMConfig()

        super().__init__(
            model=model,
            llm_config=llm_config,
            api_key_env_var="KIMI_API_KEY",
            base_url="https://api.moonshot.cn/v1"
        )
        logger.info(f"KimiLLM initialized with model: {self.model}")
