import logging
from typing import Optional
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM

logger = logging.getLogger(__name__)

class QwenLLM(OpenAICompatibleLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        if model is None:
            model = LLMModel['qwen3-max-preview']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(
            model=model,
            llm_config=llm_config,
            api_key_env_var="DASHSCOPE_API_KEY",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )
        logger.info(f"QwenLLM initialized with model: {self.model}")

    async def cleanup(self):
        await super().cleanup()
