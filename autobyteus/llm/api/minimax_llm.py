import logging
from typing import Optional
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.api.openai_compatible_llm import OpenAICompatibleLLM

logger = logging.getLogger(__name__)

class MinimaxLLM(OpenAICompatibleLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        # Provide defaults if not specified
        if model is None:
            # Default to a reasonable model if none provided
            # Note: This requires the model to be registered in LLMFactory or passed explicitly
            from autobyteus.llm.llm_factory import LLMFactory
            # We can't easily default to a specific LLMModel instance here without importing from Factory 
            # (which causes circular import) or Models (which are registered in Factory).
            # So we rely on the caller to provide it, or handle it gracefully.
            # However, for consistency with other implementations like OpenAILLM, 
            # we might want to fail or rely on a generic fallback if needed.
            # But usually this is called via factory.
            pass

        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(
            model=model, 
            llm_config=llm_config,
            api_key_env_var="MINIMAX_API_KEY",
            base_url="https://api.minimax.io/v1"
        )
        logger.info(f"MinimaxLLM initialized with model: {self.model}")

    async def cleanup(self):
        await super().cleanup()
