# file: autobyteus/autobyteus/agent_team/bootstrap_steps/agent_configuration_preparation_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent.message.send_message_to import SendMessageTo

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class AgentConfigurationPreparationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to prepare the final, immutable configuration for every
    agent in the team. It injects team-specific context, applies team-level
    settings like tool format overrides, and prepares the final coordinator prompt.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing AgentConfigurationPreparationStep to prepare all agent configurations.")
        
        team_manager = context.team_manager
        if not team_manager:
            logger.error(f"Team '{team_id}': TeamManager not found in context during agent config preparation.")
            return False

        try:
            coordinator_node_config = context.config.coordinator_node
            
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

                # --- Team-level Setting Propagation ---
                # If the team config specifies a tool format, it overrides any agent-level setting.
                if context.config.use_xml_tool_format is not None:
                    final_config.use_xml_tool_format = context.config.use_xml_tool_format
                    logger.debug(f"Team '{team_id}': Applied team-level use_xml_tool_format={final_config.use_xml_tool_format} to agent '{unique_name}'.")


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
                
                # If this is the coordinator, apply the prompt that was prepared in the previous step.
                if node_config_wrapper == coordinator_node_config:
                    coordinator_prompt = context.state.prepared_coordinator_prompt
                    if coordinator_prompt:
                        final_config.system_prompt = coordinator_prompt
                        logger.info(f"Team '{team_id}': Applied dynamic prompt to coordinator '{unique_name}'.")

                # Store the final, ready-to-use config in the team's state
                context.state.final_agent_configs[unique_name] = final_config
                logger.info(f"Team '{team_id}': Prepared final config for agent '{unique_name}' with user-defined tools: {[t.get_name() for t in final_config.tools]}")
            
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Failed during agent configuration preparation: {e}", exc_info=True)
            return False
