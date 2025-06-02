# file: autobyteus/autobyteus/agent/bootstrap_steps/llm_config_finalization_step.py
import logging
from typing import TYPE_CHECKING

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager

logger = logging.getLogger(__name__)

class LLMConfigFinalizationStep(BaseBootstrapStep):
    """
    Bootstrap step for finalizing the LLM configuration.
    This step does not notify a phase change itself, as it's considered part of
    the broader LLM initialization phase triggered by LLMInstanceCreationStep.
    """
    def __init__(self):
        logger.debug("LLMConfigFinalizationStep initialized.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool: # phase_manager passed but not used for notification
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Executing LLMConfigFinalizationStep.")

        try:
            processed_system_prompt = context.state.processed_system_prompt
            if processed_system_prompt is None: # pragma: no cover
                raise ValueError("Processed system prompt not found in agent state. Cannot finalize LLMConfig.")

            llm_model_name = context.config.llm_model_name
            custom_llm_config_from_agent_config = context.config.custom_llm_config

            try:
                llm_model_enum_instance = LLMModel[llm_model_name]
            except KeyError: # pragma: no cover
                logger.error(f"Invalid llm_model_name '{llm_model_name}' in agent config for agent '{agent_id}'.")
                raise ValueError(f"Invalid llm_model_name '{llm_model_name}' for LLMConfig finalization.")

            # Start with LLMConfig defaults, then layer model defaults, then custom config
            final_llm_config = LLMConfig() 
            if llm_model_enum_instance.default_config:
                final_llm_config = LLMConfig.from_dict(llm_model_enum_instance.default_config.to_dict())
            
            if custom_llm_config_from_agent_config:
                logger.debug(f"Agent '{agent_id}': Merging custom LLMConfig from AgentConfig.")
                final_llm_config.merge_with(custom_llm_config_from_agent_config)

            final_llm_config.system_message = processed_system_prompt
            
            context.state.final_llm_config_for_creation = final_llm_config
            logger.info(f"Agent '{agent_id}': LLMConfig finalized and stored in state. System message length: {len(final_llm_config.system_message)}.")
            return True
        except Exception as e:
            error_message = f"Agent '{agent_id}': Critical failure during LLMConfig finalization: {e}"
            logger.error(error_message, exc_info=True)
            await context.input_event_queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
            return False
