"""
Bootstrap step to finalize each agent's system prompt by injecting a dynamically
generated team manifest into any prompt template that contains the `{{team}}`
placeholder.
"""
import logging
from typing import TYPE_CHECKING, Dict, List

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.context import AgentTeamConfig

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext


logger = logging.getLogger(__name__)


class TeamManifestInjectionStep(BaseAgentTeamBootstrapStep):
    """
    Generates a per-agent prompt with the team manifest injected. The manifest
    omits the current agent so that it only lists collaborators. Results are
    stored in `context.state.prepared_agent_prompts` for later application.
    """

    async def execute(self, context: 'AgentTeamContext') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing TeamManifestInjectionStep.")

        try:
            prepared_prompts: Dict[str, str] = {}

            for node_config_wrapper in context.config.nodes:
                # Only prepare prompts for direct agent members (skip sub-teams)
                if node_config_wrapper.is_sub_team:
                    continue

                node_definition = node_config_wrapper.node_definition
                if not isinstance(node_definition, AgentConfig):
                    logger.warning(
                        f"Team '{team_id}': Node '{node_config_wrapper.name}' is not an AgentConfig. "
                        "Skipping prompt preparation for this node."
                    )
                    continue

                prompt_template = node_definition.system_prompt
                if not prompt_template or "{{team}}" not in prompt_template:
                    # No placeholder to replace; skip to keep original prompt intact.
                    continue

                team_manifest = self._generate_team_manifest(context, exclude_name=node_config_wrapper.name)
                finalized_prompt = prompt_template.replace("{{team}}", team_manifest)
                prepared_prompts[node_config_wrapper.name] = finalized_prompt
                logger.debug(
                    f"Team '{team_id}': Prepared prompt for agent '{node_config_wrapper.name}' "
                    f"with team manifest."
                )

            context.state.prepared_agent_prompts = prepared_prompts
            logger.info(f"Team '{team_id}': Team prompts prepared for {len(prepared_prompts)} agent(s).")
            return True
        except Exception as exc:
            logger.error(f"Team '{team_id}': Failed to prepare team prompts: {exc}", exc_info=True)
            return False

    def _generate_team_manifest(self, context: 'AgentTeamContext', exclude_name: str) -> str:
        """
        Builds a manifest string of all team members except the given agent.
        Includes sub-teams so agents see the full collaboration surface.
        """
        prompt_parts: List[str] = []

        for node in sorted(list(context.config.nodes), key=lambda n: n.name):
            if node.name == exclude_name:
                continue

            node_def = node.node_definition
            description = "No description available."

            if isinstance(node_def, AgentConfig):
                description = node_def.description
            elif isinstance(node_def, AgentTeamConfig):
                description = node_def.role or node_def.description

            prompt_parts.append(f"- name: {node.name}\n  description: {description}")

        if not prompt_parts:
            return "You are working alone. You have no team members to delegate to."

        return "\n".join(prompt_parts)
