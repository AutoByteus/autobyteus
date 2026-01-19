import logging
from typing import Optional, Dict, Any
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM

logger = logging.getLogger(__name__)

def _normalize_zhipu_extra_params(extra_params: Dict[str, Any]) -> Dict[str, Any]:
    if not extra_params:
        return {}

    params = dict(extra_params)
    thinking_type = params.pop("thinking_type", None)

    if thinking_type is not None:
        thinking = dict(params.get("thinking") or {})

        if thinking_type is not None:
            thinking["type"] = thinking_type

        params["thinking"] = thinking

    return params

class ZhipuLLM(OpenAICompatibleLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        # Provide defaults if not specified
        if model is None:
            model = LLMModel['glm-4.7']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(
            model=model,
            llm_config=llm_config,
            api_key_env_var="ZHIPU_API_KEY",
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        )
        if self.config and isinstance(self.config.extra_params, dict):
            self.config.extra_params = _normalize_zhipu_extra_params(self.config.extra_params)
        logger.info(f"ZhipuLLM initialized with model: {self.model}")

    async def cleanup(self):
        await super().cleanup()
