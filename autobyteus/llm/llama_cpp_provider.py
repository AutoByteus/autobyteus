import logging
import os
import asyncio
from autobyteus.llm.runtimes import LLMRuntime

logger = logging.getLogger(__name__)

class LlamaCppModelProvider:
    """
    Discovers and auto-loads llama.cpp models specified in environment variables at startup.
    """
    @staticmethod
    def discover_and_register():
        # This function is async internally, so we run it in a new event loop
        # to ensure compatibility with synchronous factory initialization.
        try:
            asyncio.run(LlamaCppModelProvider._discover_and_register_async())
        except Exception as e:
            logger.error(f"Failed during async discovery for Llama.cpp: {e}")

    @staticmethod
    async def _discover_and_register_async():
        from autobyteus.llm.local_model_runtime_manager import LocalModelRuntimeManager
        
        models_to_load = os.getenv("LLAMACPP_MODELS_AUTOLOAD")
        if not models_to_load:
            logger.info("LLAMACPP_MODELS_AUTOLOAD not set. Skipping auto-loading of llama.cpp models.")
            return

        manager = LocalModelRuntimeManager()
        model_paths = [path.strip() for path in models_to_load.split(',')]
        
        for model_path in model_paths:
            if not model_path:
                continue
            try:
                logger.info(f"Auto-loading llama.cpp model from: {model_path}")
                await manager.load_model(model_path=model_path, runtime=LLMRuntime.LLAMA_CPP)
            except Exception as e:
                logger.error(f"Failed to auto-load llama.cpp model '{model_path}': {e}")
