# file: autobyteus/autobyteus/agent/shutdown_steps/llm_instance_cleanup_step.py
import asyncio
import logging
from typing import TYPE_CHECKING

from .base_shutdown_step import BaseShutdownStep

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class LLMInstanceCleanupStep(BaseShutdownStep):
    """
    Shutdown step for cleaning up the agent's LLM instance.
    """
    def __init__(self):
        logger.debug("LLMInstanceCleanupStep initialized.")

    async def execute(self, context: 'AgentContext') -> bool:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Executing LLMInstanceCleanupStep.")

        llm_instance = context.llm_instance
        if not llm_instance:
            logger.debug(f"Agent '{agent_id}': No LLM instance found in context. Skipping cleanup.")
            return True

        if hasattr(llm_instance, 'cleanup') and callable(getattr(llm_instance, 'cleanup')):
            try:
                logger.info(f"Agent '{agent_id}': Running LLM instance cleanup for '{llm_instance.__class__.__name__}'.")
                cleanup_func = llm_instance.cleanup
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()
                logger.info(f"Agent '{agent_id}': LLM instance cleanup completed successfully.")
                return True
            except Exception as e:
                error_message = f"Agent '{agent_id}': Error during LLM instance cleanup: {e}"
                logger.error(error_message, exc_info=True)
                return False
        else:
            logger.debug(f"Agent '{agent_id}': LLM instance of type '{llm_instance.__class__.__name__}' does not have a 'cleanup' method. Skipping.")
            return True
