# file: autobyteus/autobyteus/agent_team/bootstrap_steps/agent_team_bootstrapper.py
import logging
from typing import TYPE_CHECKING, List, Optional

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent_team.bootstrap_steps.agent_team_runtime_queue_initialization_step import AgentTeamRuntimeQueueInitializationStep
from autobyteus.agent_team.bootstrap_steps.team_context_initialization_step import TeamContextInitializationStep
from autobyteus.agent_team.bootstrap_steps.task_notifier_initialization_step import TaskNotifierInitializationStep
from autobyteus.agent_team.bootstrap_steps.coordinator_prompt_preparation_step import CoordinatorPromptPreparationStep
from autobyteus.agent_team.bootstrap_steps.agent_configuration_preparation_step import AgentConfigurationPreparationStep
from autobyteus.agent_team.bootstrap_steps.coordinator_initialization_step import CoordinatorInitializationStep
from autobyteus.agent_team.events.agent_team_events import AgentTeamReadyEvent

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class AgentTeamBootstrapper:
    """Orchestrates the agent team's bootstrapping process."""
    def __init__(self, steps: Optional[List[BaseAgentTeamBootstrapStep]] = None):
        self.bootstrap_steps = steps or [
            AgentTeamRuntimeQueueInitializationStep(),
            TeamContextInitializationStep(),
            TaskNotifierInitializationStep(),
            CoordinatorPromptPreparationStep(),
            AgentConfigurationPreparationStep(),
            CoordinatorInitializationStep(),
        ]

    async def run(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        await phase_manager.notify_bootstrapping_started()
        logger.info(f"Team '{team_id}': Bootstrapper starting.")

        for step in self.bootstrap_steps:
            step_name = step.__class__.__name__
            logger.debug(f"Team '{team_id}': Executing bootstrap step: {step_name}")
            if not await step.execute(context, phase_manager):
                error_message = f"Bootstrap step {step_name} failed."
                logger.error(f"Team '{team_id}': {error_message}")
                await phase_manager.notify_error_occurred(error_message, f"Failed during bootstrap step '{step_name}'.")
                return False
        
        logger.info(f"Team '{team_id}': All bootstrap steps completed successfully.")
        if context.state.input_event_queues:
            await context.state.input_event_queues.enqueue_internal_system_event(AgentTeamReadyEvent())
        else:
            logger.critical(f"Team '{team_id}': Bootstrap succeeded but queues not available.")
            await phase_manager.notify_error_occurred("Queues unavailable after bootstrap.", "")
            return False
            
        return True
