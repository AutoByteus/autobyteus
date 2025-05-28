# file: autobyteus/autobyteus/agent/handlers/create_llm_instance_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import CreateLLMInstanceEvent, AgentStartedEvent, AgentErrorEvent

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class CreateLLMInstanceEventHandler(AgentEventHandler):
    """
    Handles the CreateLLMInstanceEvent. This handler is responsible for:
    1. Retrieving the LLM model name from agent config and final LLMConfig from agent state.
    2. Instantiating the BaseLLM for the agent using an LLMFactory.
    3. Updating the AgentContext's state with the instantiated LLM.
    4. Enqueuing an AgentStartedEvent to signal that the agent is fully ready.
    """

    def __init__(self, llm_factory: 'LLMFactory'):
        if llm_factory is None:
            raise ValueError("CreateLLMInstanceEventHandler requires an LLMFactory instance.")
        self.llm_factory = llm_factory
        logger.info("CreateLLMInstanceEventHandler initialized.")

    async def handle(self,
                     event: CreateLLMInstanceEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, CreateLLMInstanceEvent):
            logger.warning(f"CreateLLMInstanceEventHandler received non-CreateLLMInstanceEvent: {type(event)}. Skipping.")
            return

        agent_id = context.config.agent_id
        logger.info(f"Agent '{agent_id}': Handling CreateLLMInstanceEvent.")

        try:
            llm_model_name = context.config.llm_model_name
            final_llm_config = context.state.final_llm_config_for_creation

            if final_llm_config is None:
                raise ValueError("Final LLMConfig not found in agent state. Cannot create LLM instance.")
            if llm_model_name is None: # Should be caught by AgentConfig validation
                 raise ValueError("LLM model name not found in agent config.")

            llm_instance = self.llm_factory.create_llm(
                model_identifier=llm_model_name,
                llm_config=final_llm_config
            )
            logger.info(f"Agent '{agent_id}': LLM instance ({llm_instance.__class__.__name__}) created successfully.")

            context.state.llm_instance = llm_instance
            logger.debug(f"Agent '{agent_id}': LLM instance set in AgentContext.state.")

            await context.state.queues.enqueue_internal_system_event(AgentStartedEvent())
            logger.info(f"Agent '{agent_id}': LLM instantiation complete. Enqueued AgentStartedEvent.")

        except Exception as e:
            error_message = f"Agent '{agent_id}': Failed to create LLM instance: {e}"
            logger.error(error_message, exc_info=True)
            await context.state.queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
