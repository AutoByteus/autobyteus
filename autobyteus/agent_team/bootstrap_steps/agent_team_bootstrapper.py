# file: autobyteus/autobyteus/agent_team/bootstrap_steps/agent_team_bootstrapper.py
import logging
from typing import TYPE_CHECKING, List, Optional

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent_team.bootstrap_steps.team_context_initialization_step import TeamContextInitializationStep
from autobyteus.agent_team.bootstrap_steps.task_notifier_initialization_step import TaskNotifierInitializationStep
from autobyteus.agent_team.bootstrap_steps.team_manifest_injection_step import TeamManifestInjectionStep
from autobyteus.agent_team.bootstrap_steps.agent_configuration_preparation_step import AgentConfigurationPreparationStep
from autobyteus.agent_team.bootstrap_steps.coordinator_initialization_step import CoordinatorInitializationStep
if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class AgentTeamBootstrapper:
    """Orchestrates the agent team's bootstrapping process."""
    def __init__(self, steps: Optional[List[BaseAgentTeamBootstrapStep]] = None):
        self.bootstrap_steps = steps or [
            TeamContextInitializationStep(),
            TaskNotifierInitializationStep(),
            TeamManifestInjectionStep(),
            AgentConfigurationPreparationStep(),
            CoordinatorInitializationStep(),
        ]

    async def run(self, context: 'AgentTeamContext') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Bootstrapper starting.")

        for step in self.bootstrap_steps:
            step_name = step.__class__.__name__
            logger.debug(f"Team '{team_id}': Executing bootstrap step: {step_name}")
            if not await step.execute(context):
                error_message = f"Bootstrap step {step_name} failed."
                logger.error(f"Team '{team_id}': {error_message}")
                return False
        
        logger.info(f"Team '{team_id}': All bootstrap steps completed successfully.")
        if not context.state.input_event_queues:
            logger.critical(f"Team '{team_id}': Bootstrap succeeded but queues not available.")
            return False

        return True
