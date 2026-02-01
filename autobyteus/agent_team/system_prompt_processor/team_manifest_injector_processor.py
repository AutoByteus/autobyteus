# file: autobyteus/autobyteus/agent_team/system_prompt_processor/team_manifest_injector_processor.py
import logging
from typing import Dict, List, TYPE_CHECKING

from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.agent_team.context import AgentTeamConfig

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)


class TeamManifestInjectorProcessor(BaseSystemPromptProcessor):
    """
    Injects a team manifest into the system prompt for agents that belong to a team.
    If the prompt contains {{team}}, the placeholder is replaced. Otherwise, the
    manifest is appended as a dedicated section.
    """

    @classmethod
    def get_name(cls) -> str:
        return "TeamManifestInjector"

    @classmethod
    def get_order(cls) -> int:
        return 450

    def process(
        self,
        system_prompt: str,
        tool_instances: Dict[str, 'BaseTool'],
        agent_id: str,
        context: 'AgentContext',
    ) -> str:
        team_context = context.custom_data.get("team_context")
        if team_context is None:
            logger.debug(f"Agent '{agent_id}': No team_context found; skipping team manifest injection.")
            return system_prompt

        manifest = self._generate_team_manifest(team_context, exclude_name=context.config.name)

        if "{{team}}" in system_prompt:
            logger.info(f"Agent '{agent_id}': Replacing {{team}} placeholder with team manifest.")
            return system_prompt.replace("{{team}}", manifest)

        logger.info(f"Agent '{agent_id}': Appending team manifest to system prompt.")
        return system_prompt + "\n\n## Team Manifest\n\n" + manifest

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

            if hasattr(node_def, "description") and isinstance(node_def.description, str):
                description = node_def.description
            elif isinstance(node_def, AgentTeamConfig):
                description = node_def.role or node_def.description

            prompt_parts.append(f"- name: {node.name}\n  description: {description}")

        if not prompt_parts:
            return "You are working alone. You have no team members to delegate to."

        return "\n".join(prompt_parts)
