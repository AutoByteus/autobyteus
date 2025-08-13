# file: autobyteus/autobyteus/agent_team/bootstrap_steps/coordinator_prompt_preparation_step.py
import logging
from typing import TYPE_CHECKING, List

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.context import AgentTeamConfig

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class CoordinatorPromptPreparationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to finalize the coordinator's system prompt by injecting a
    dynamically generated team manifest into a user-defined prompt template.
    The user is expected to provide a `system_prompt` in the coordinator's
    AgentConfig with a `{{team}}` placeholder.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing CoordinatorPromptPreparationStep.")
        try:
            coordinator_node_config_wrapper = context.config.coordinator_node
            
            # The coordinator must be an agent with a defined config.
            if not isinstance(coordinator_node_config_wrapper.node_definition, AgentConfig):
                logger.error(f"Team '{team_id}': Coordinator node '{coordinator_node_config_wrapper.name}' is not defined by an AgentConfig. Cannot prepare prompt.")
                return False
            
            coordinator_agent_config: AgentConfig = coordinator_node_config_wrapper.node_definition
            
            # Start with the user's provided prompt template.
            prompt_template = coordinator_agent_config.system_prompt
            if not prompt_template:
                logger.warning(f"Team '{team_id}': Coordinator '{coordinator_agent_config.name}' has no system_prompt defined. No prompt will be applied.")
                context.state.prepared_coordinator_prompt = ""
                return True

            team_manifest = self._generate_team_manifest(context)
            
            # Inject the manifest into the template.
            if "{{team}}" in prompt_template:
                final_prompt = prompt_template.replace("{{team}}", team_manifest)
                logger.debug(f"Team '{team_id}': Injected team manifest into coordinator's system prompt.")
            else:
                final_prompt = prompt_template
                logger.warning(f"Team '{team_id}': The coordinator's system prompt does not contain a '{{team}}' placeholder. The team manifest will not be injected.")
            
            # Store the finalized prompt in the state for the AgentToolInjectionStep to use.
            context.state.prepared_coordinator_prompt = final_prompt

            logger.info(f"Team '{team_id}': Coordinator prompt prepared successfully and stored in state.")
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Failed to prepare coordinator prompt: {e}", exc_info=True)
            return False

    def _generate_team_manifest(self, context: 'AgentTeamContext') -> str:
        """Generates a string manifest of all non-coordinator team members."""
        prompt_parts: List[str] = []
        coordinator_node = context.config.coordinator_node
        member_nodes = {node for node in context.config.nodes if node != coordinator_node}

        if not member_nodes:
            return "You are working alone. You have no team members to delegate to."

        # Sort for deterministic prompt generation
        for node in sorted(list(member_nodes), key=lambda n: n.name):
            node_def = node.node_definition
            description = "No description available."
            
            # --- THE FIX ---
            # Use the 'description' for an AgentConfig and the 'role' for an AgentTeamConfig (sub-team).
            if isinstance(node_def, AgentConfig):
                description = node_def.description
            elif isinstance(node_def, AgentTeamConfig):
                # A sub-team's role is its most concise and relevant description for a parent coordinator.
                description = node_def.role or node_def.description
            
            prompt_parts.append(f"- name: {node.name}\n  description: {description}")
        
        return "\n".join(prompt_parts)
