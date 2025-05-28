# file: autobyteus/autobyteus/agent/handlers/initialize_llm_event_handler.py
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import InitializeLLMEvent, AgentStartedEvent, AgentErrorEvent
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext
    from autobyteus.llm.llm_factory import LLMFactory
    from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry, BaseSystemPromptProcessor

logger = logging.getLogger(__name__)

class InitializeLLMEventHandler(AgentEventHandler):
    """
    Handles the InitializeLLMEvent. This handler is responsible for:
    1. Processing the agent's system prompt using configured SystemPromptProcessors.
    2. Creating the final LLMConfig for the agent.
    3. Instantiating the BaseLLM for the agent using an LLMFactory.
    4. Updating the AgentContext's state with the instantiated LLM.
    5. Enqueuing an AgentStartedEvent to signal that the agent is fully ready.
    """

    def __init__(self, 
                 llm_factory: 'LLMFactory', 
                 system_prompt_processor_registry: 'SystemPromptProcessorRegistry'):
        if llm_factory is None:
            raise ValueError("InitializeLLMEventHandler requires an LLMFactory instance.")
        if system_prompt_processor_registry is None:
            raise ValueError("InitializeLLMEventHandler requires a SystemPromptProcessorRegistry instance.")
            
        self.llm_factory = llm_factory
        self.system_prompt_processor_registry = system_prompt_processor_registry
        logger.info("InitializeLLMEventHandler initialized.")

    async def handle(self,
                     event: InitializeLLMEvent,
                     context: 'AgentContext') -> None: # context is composite
        if not isinstance(event, InitializeLLMEvent):
            logger.warning(f"InitializeLLMEventHandler received non-InitializeLLMEvent: {type(event)}. Skipping.")
            return

        agent_id = context.config.agent_id # Access via context.config
        logger.info(f"Agent '{agent_id}': Handling InitializeLLMEvent. Preparing to set up LLM.")

        try:
            # 1. Process System Prompt
            current_system_prompt = context.config.definition.system_prompt
            processor_names_to_apply = context.config.definition.system_prompt_processor_names
            
            if not processor_names_to_apply:
                logger.debug(f"Agent '{agent_id}': No system prompt processors configured. Using system prompt template as is.")
            else:
                logger.debug(f"Agent '{agent_id}': Applying system prompt processors: {processor_names_to_apply}")
                for processor_name in processor_names_to_apply:
                    processor_instance: Optional['BaseSystemPromptProcessor'] = self.system_prompt_processor_registry.get_processor(processor_name)
                    if processor_instance:
                        try:
                            logger.debug(f"Agent '{agent_id}': Applying system prompt processor '{processor_name}' (class: {processor_instance.__class__.__name__}).")
                            current_system_prompt = processor_instance.process(
                                system_prompt=current_system_prompt,
                                tool_instances=context.config.tool_instances, # Access via context.config
                                agent_id=agent_id
                            )
                            logger.info(f"Agent '{agent_id}': System prompt processor '{processor_name}' applied successfully.")
                        except Exception as e_proc:
                            logger.error(f"Agent '{agent_id}': Error applying system prompt processor '{processor_name}': {e_proc}. "
                                         f"Continuing with prompt from before this processor.", exc_info=True)
                    else:
                        logger.warning(f"Agent '{agent_id}': System prompt processor name '{processor_name}' not found in registry. Skipping.")
            
            processed_system_prompt = current_system_prompt
            logger.info(f"Agent '{agent_id}': System prompt processed. Final prompt (first 100 chars): '{processed_system_prompt[:100]}...'")

            # 2. Create LLMConfig
            llm_model_name = context.config.llm_model_name # Access via context.config
            custom_llm_config_for_init = context.config.custom_llm_config # Access via context.config

            config_source_log_parts = []
            try:
                llm_model_enum_instance = LLMModel[llm_model_name] 
            except KeyError:
                logger.error(f"Invalid llm_model_name '{llm_model_name}' in context.config.")
                raise ValueError(f"Invalid llm_model_name '{llm_model_name}' for LLM initialization.")

            if llm_model_enum_instance.default_config:
                final_llm_config = LLMConfig.from_dict(llm_model_enum_instance.default_config.to_dict())
                config_source_log_parts.append(f"base from model '{llm_model_name}' default_config")
            else:
                logger.warning(f"LLMModel '{llm_model_name}' does not have a default_config. Initializing LLMConfig with class defaults.")
                final_llm_config = LLMConfig()
                config_source_log_parts.append("LLMConfig class defaults")
            
            if custom_llm_config_for_init:
                logger.debug(f"Applying custom LLMConfig provided at agent creation for '{agent_id}'.")
                final_llm_config.merge_with(custom_llm_config_for_init)
                config_source_log_parts.append("merged with custom_llm_config")

            final_llm_config.system_message = processed_system_prompt
            config_source_log_parts.append("processed system_prompt applied")
            
            config_source_log = ", ".join(config_source_log_parts)
            logger.debug(f"LLMConfig for agent '{agent_id}' created. Based on: {config_source_log}. "
                         f"Final temp: {final_llm_config.temperature}, sys_msg: '{final_llm_config.system_message[:50]}...'")

            # 3. Instantiate LLM
            llm_instance = self.llm_factory.create_llm(
                model_identifier=llm_model_name, 
                llm_config=final_llm_config
            )
            logger.info(f"Agent '{agent_id}': LLM instance ({llm_instance.__class__.__name__}) created successfully.")

            # 4. Update AgentContext's state
            context.state.llm_instance = llm_instance # Access via context.state
            logger.debug(f"Agent '{agent_id}': LLM instance set in AgentContext.state.")

            # 5. Enqueue AgentStartedEvent
            await context.state.queues.enqueue_internal_system_event(AgentStartedEvent()) # Access via context.state
            logger.info(f"Agent '{agent_id}': LLM initialization complete. Enqueued AgentStartedEvent.")

        except Exception as e:
            error_message = f"Agent '{agent_id}': Failed to initialize LLM: {e}"
            logger.error(error_message, exc_info=True)
            await context.state.queues.enqueue_internal_system_event( # Access via context.state
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
