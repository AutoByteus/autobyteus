# file: autobyteus/autobyteus/agent/bootstrap_steps/agent_runtime_queue_initialization_step.py
import logging
from typing import TYPE_CHECKING

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.events import AgentErrorEvent, AgentInputEventQueueManager
# AgentOutputDataManager is no longer initialized here.

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.phases import AgentPhaseManager

logger = logging.getLogger(__name__)

class AgentRuntimeQueueInitializationStep(BaseBootstrapStep):
    """
    Bootstrap step for initializing the agent's runtime INPUT event queues.
    These queues are created within the AgentWorker's event loop.
    Output data is now handled by emitting events via AgentExternalEventNotifier.
    """
    def __init__(self, input_queue_size: int = 0): # Removed output_queue_size
        self.input_queue_size = input_queue_size
        logger.debug(f"AgentRuntimeQueueInitializationStep initialized with input_q_size={input_queue_size}.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Executing AgentRuntimeQueueInitializationStep (for input queues).")

        try:
            if context.state.input_event_queues is not None: # Check only input queues
                logger.warning(f"Agent '{agent_id}': Input runtime queues seem to be already initialized. Overwriting. This might indicate a logic error.")

            input_queues = AgentInputEventQueueManager(queue_size=self.input_queue_size)
            context.state.input_event_queues = input_queues
            # context.state.output_data_queues is no longer set here.

            logger.info(f"Agent '{agent_id}': AgentInputEventQueueManager initialized and set in agent state.")
            if context.state.input_event_queues is None: # pragma: no cover
                raise RuntimeError("Input event queue manager was not successfully set in agent state during AgentRuntimeQueueInitializationStep.")
            
            return True
        except Exception as e:
            error_message = f"Agent '{agent_id}': Critical failure during AgentRuntimeQueueInitializationStep (input queues): {e}"
            logger.error(error_message, exc_info=True)
            
            # Attempt to enqueue an error event if input_event_queues was partially created
            # This check itself might be problematic if input_queues is the thing that failed.
            # However, if it failed *after* assigning self.input_event_queues, this might work.
            if context.state.input_event_queues and context.state.input_event_queues.internal_system_event_queue: # pragma: no cover
                 await context.state.input_event_queues.enqueue_internal_system_event(
                     AgentErrorEvent(error_message=error_message, exception_details=str(e))
                 )
            else: # pragma: no cover
                 logger.error(f"Agent '{agent_id}': Cannot enqueue AgentErrorEvent as input_event_queues are not available after AgentRuntimeQueueInitializationStep failure.")
            return False
