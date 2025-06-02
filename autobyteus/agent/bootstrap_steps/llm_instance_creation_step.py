# file: autobyteus/autobyteus/agent/bootstrap_steps/llm_instance_creation_step.py
import logging
from typing import TYPE_CHECKING

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.events import AgentErrorEvent

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class LLMInstanceCreationStep(BaseBootstrapStep):
    """
    Bootstrap step for creating the LLM instance.
    """
    def __init__(self, llm_factory: 'LLMFactory'):
        if llm_factory is None: # pragma: no cover
            raise ValueError("LLMInstanceCreationStep requires an LLMFactory instance.")
        self.llm_factory = llm_factory
        logger.debug("LLMInstanceCreationStep initialized.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        agent_id = context.agent_id
        phase_manager.notify_initializing_llm() # Covers both config finalization and instance creation
        logger.info(f"Agent '{agent_id}': Executing LLMInstanceCreationStep.")

        try:
            llm_model_name = context.config.llm_model_name
            final_llm_config = context.state.final_llm_config_for_creation

            if final_llm_config is None: # pragma: no cover
                raise ValueError("Final LLMConfig not found in agent state. LLMConfigFinalizationStep might have failed or was skipped.")
            if llm_model_name is None: # pragma: no cover
                 raise ValueError("LLM model name not found in agent config.")

            llm_instance = self.llm_factory.create_llm(
                model_identifier=llm_model_name,
                llm_config=final_llm_config
            )
            context.state.llm_instance = llm_instance
            logger.info(f"Agent '{agent_id}': LLM instance ({llm_instance.__class__.__name__}) created successfully.")
            return True
        except Exception as e:
            error_message = f"Agent '{agent_id}': Critical failure creating LLM instance: {e}"
            logger.error(error_message, exc_info=True)
            await context.input_event_queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
            return False
