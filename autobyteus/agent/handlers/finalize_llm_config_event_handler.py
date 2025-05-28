# file: autobyteus/autobyteus/agent/handlers/finalize_llm_config_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import FinalizeLLMConfigEvent, CreateLLMInstanceEvent, AgentErrorEvent
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel # For default config retrieval

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext

logger = logging.getLogger(__name__)

class FinalizeLLMConfigEventHandler(AgentEventHandler):
    """
    Handles the FinalizeLLMConfigEvent. This handler is responsible for:
    1. Retrieving the processed system prompt from agent state.
    2. Retrieving LLM model name and custom LLM config from agent config.
    3. Creating the final LLMConfig object.
    4. Storing the final LLMConfig in the agent's runtime state.
    5. Enqueuing a CreateLLMInstanceEvent to proceed with LLM instantiation.
    """

    def __init__(self):
        # This handler might not need specific dependencies if all data comes from context
        logger.info("FinalizeLLMConfigEventHandler initialized.")

    async def handle(self,
                     event: FinalizeLLMConfigEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, FinalizeLLMConfigEvent):
            logger.warning(f"FinalizeLLMConfigEventHandler received non-FinalizeLLMConfigEvent: {type(event)}. Skipping.")
            return

        agent_id = context.config.agent_id
        logger.info(f"Agent '{agent_id}': Handling FinalizeLLMConfigEvent.")

        try:
            processed_system_prompt = context.state.processed_system_prompt
            if processed_system_prompt is None:
                raise ValueError("Processed system prompt not found in agent state. Cannot finalize LLMConfig.")

            llm_model_name = context.config.llm_model_name
            custom_llm_config_from_agent_config = context.config.custom_llm_config

            config_source_log_parts = []
            try:
                llm_model_enum_instance = LLMModel[llm_model_name]
            except KeyError:
                logger.error(f"Invalid llm_model_name '{llm_model_name}' in context.config.")
                raise ValueError(f"Invalid llm_model_name '{llm_model_name}' for LLMConfig finalization.")

            if llm_model_enum_instance.default_config:
                final_llm_config = LLMConfig.from_dict(llm_model_enum_instance.default_config.to_dict())
                config_source_log_parts.append(f"base from model '{llm_model_name}' default_config")
            else:
                logger.warning(f"LLMModel '{llm_model_name}' does not have a default_config. Initializing LLMConfig with class defaults.")
                final_llm_config = LLMConfig()
                config_source_log_parts.append("LLMConfig class defaults")
            
            if custom_llm_config_from_agent_config:
                logger.debug(f"Applying custom LLMConfig (from AgentConfig) for '{agent_id}'.")
                final_llm_config.merge_with(custom_llm_config_from_agent_config)
                config_source_log_parts.append("merged with custom_llm_config from AgentConfig")

            final_llm_config.system_message = processed_system_prompt
            config_source_log_parts.append("processed system_prompt applied")
            
            config_source_log = ", ".join(config_source_log_parts)
            logger.debug(f"LLMConfig for agent '{agent_id}' finalized. Based on: {config_source_log}. "
                         f"Final temp: {final_llm_config.temperature}, sys_msg: '{final_llm_config.system_message[:50]}...'")

            context.state.final_llm_config_for_creation = final_llm_config
            logger.info(f"Agent '{agent_id}': Final LLMConfig stored in state.")

            await context.state.queues.enqueue_internal_system_event(CreateLLMInstanceEvent())
            logger.debug(f"Agent '{agent_id}': Enqueued CreateLLMInstanceEvent.")

        except Exception as e:
            error_message = f"Agent '{agent_id}': Failed during LLMConfig finalization: {e}"
            logger.error(error_message, exc_info=True)
            await context.state.queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
