import logging
import os
import sys
import asyncio
from autobyteus.llm.runtimes import LLMRuntime

logger = logging.getLogger(__name__)

class MlxModelProvider:
    """
    Discovers and auto-loads MLX models specified in environment variables at startup.
    This provider only runs on macOS.
    """
    @staticmethod
    def discover_and_register():
        if sys.platform != "darwin":
            logger.debug("Not on macOS, skipping MLX model discovery.")
            return

        try:
            asyncio.run(MlxModelProvider._discover_and_register_async())
        except Exception as e:
            logger.error(f"Failed during async discovery for MLX: {e}")

    @staticmethod
    async def _discover_and_register_async():
        from autobyteus.llm.local_model_runtime_manager import LocalModelRuntimeManager

        models_to_load = os.getenv("MLX_MODELS_AUTOLOAD")
        if not models_to_load:
            logger.info("MLX_MODELS_AUTOLOAD not set. Skipping auto-loading of MLX models.")
            return
            
        manager = LocalModelRuntimeManager()
        model_ids = [mid.strip() for mid in models_to_load.split(',')]
        
        for model_id in model_ids:
            if not model_id:
                continue
            try:
                logger.info(f"Auto-loading MLX model: {model_id}")
                await manager.load_model(model_path=model_id, runtime=LLMRuntime.MLX)
            except Exception as e:
                logger.error(f"Failed to auto-load MLX model '{model_id}': {e}")
