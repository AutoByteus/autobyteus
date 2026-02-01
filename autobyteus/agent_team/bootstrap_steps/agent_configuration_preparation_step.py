# file: autobyteus/autobyteus/agent_team/bootstrap_steps/agent_configuration_preparation_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.system_prompt_processor import TeamManifestInjectorProcessor

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class AgentConfigurationPreparationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to prepare the final, immutable configuration for every
    agent in the team. It injects team-specific context, applies team-level
    settings like tool format overrides, and prepares the final coordinator prompt.
    """
    async def execute(self, context: 'AgentTeamContext') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing AgentConfigurationPreparationStep to prepare all agent configurations.")
        
        team_manager = context.team_manager
        if not team_manager:
            logger.error(f"Team '{team_id}': TeamManager not found in context during agent config preparation.")
            return False

        try:
            for node_config_wrapper in context.config.nodes:
                # This step only configures direct agent members, not sub-teams.
                if node_config_wrapper.is_sub_team:
                    continue

                unique_name = node_config_wrapper.name
                node_definition = node_config_wrapper.node_definition

                if not isinstance(node_definition, AgentConfig):
                    logger.warning(f"Team '{team_id}': Node '{unique_name}' has an unexpected definition type and will be skipped: {type(node_definition)}")
                    continue
                
                final_config = node_definition.copy()

                # --- Shared Context Injection ---
                # The shared context is injected into the initial_custom_data dictionary,
                # which is then used by the AgentFactory to create the AgentRuntimeState.
                if final_config.initial_custom_data is None:
                    final_config.initial_custom_data = {}
                final_config.initial_custom_data["team_context"] = context
                logger.debug(f"Team '{team_id}': Injected shared team_context into initial_custom_data for agent '{unique_name}'.")

                # --- Tool Injection Logic Removed ---
                # The user is now fully responsible for defining all tools an agent needs
                # in its AgentConfig. The framework no longer implicitly injects SendMessageTo.
                
                # Ensure the team manifest processor is attached for team agents.
                if final_config.system_prompt_processors is None:
                    final_config.system_prompt_processors = []
                if not any(isinstance(p, TeamManifestInjectorProcessor) for p in final_config.system_prompt_processors):
                    final_config.system_prompt_processors.append(TeamManifestInjectorProcessor())
                    logger.debug(f"Team '{team_id}': Attached TeamManifestInjectorProcessor for agent '{unique_name}'.")

                # Store the final, ready-to-use config in the team's state
                context.state.final_agent_configs[unique_name] = final_config
                logger.info(f"Team '{team_id}': Prepared final config for agent '{unique_name}' with user-defined tools: {[t.get_name() for t in final_config.tools]}")
            
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Failed during agent configuration preparation: {e}", exc_info=True)
            return False
