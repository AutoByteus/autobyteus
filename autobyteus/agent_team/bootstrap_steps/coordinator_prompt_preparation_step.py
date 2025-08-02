# file: autobyteus/autobyteus/agent_team/bootstrap_steps/coordinator_prompt_preparation_step.py
import logging
from typing import TYPE_CHECKING, Dict, Set, List

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.context.team_node_config import TeamNodeConfig
from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class CoordinatorPromptPreparationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to dynamically generate the coordinator's system prompt
    based on the agent team's structure and store it in the team's state.
    It also creates and stores a map of prompt aliases for the TeamManager to use.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing CoordinatorPromptPreparationStep.")
        try:
            coordinator_node = context.config.coordinator_node
            member_nodes = {node for node in context.config.nodes if node != coordinator_node}

            prompt_aliases = self._generate_prompt_aliases(member_nodes)
            dynamic_prompt = self._generate_prompt(context, prompt_aliases)
            
            # Create a map from the generated unique alias (e.g., "Researcher_1") back
            # to the canonical simple name (e.g., "Researcher") for the TeamManager to use.
            alias_map = {alias: node.name for node, alias in prompt_aliases.items()}
            # Also add the coordinator to the map, so it can be found by its simple name.
            alias_map[coordinator_node.name] = coordinator_node.name

            context.state.node_alias_map = alias_map
            context.state.prepared_coordinator_prompt = dynamic_prompt

            logger.info(f"Team '{team_id}': Coordinator prompt prepared successfully and stored in state.")
            logger.debug(f"Team '{team_id}': Node alias map created: {alias_map}")
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Failed to prepare coordinator prompt: {e}", exc_info=True)
            return False

    def _generate_prompt_aliases(self, member_nodes: Set[TeamNodeConfig]) -> Dict[TeamNodeConfig, str]:
        """
        Generates unique, human-readable aliases for each node to be used in the
        coordinator's prompt, preventing ambiguity if multiple nodes share the same simple name.
        """
        alias_map: Dict[TeamNodeConfig, str] = {}
        name_counts: Dict[str, int] = {}
        # Sort nodes to ensure deterministic alias generation (e.g., Researcher_1 is always the same one)
        sorted_nodes = sorted(list(member_nodes), key=lambda n: n.name)
        
        for node in sorted_nodes:
            base_name = node.name
            count = name_counts.get(base_name, 0)
            # If the base_name has been seen before, append a suffix to create a unique alias.
            unique_alias = f"{base_name}_{count + 1}" if base_name in name_counts else base_name
            alias_map[node] = unique_alias
            name_counts[base_name] = count + 1
            
        return alias_map

    def _generate_prompt(self, context: 'AgentTeamContext', prompt_aliases: Dict[TeamNodeConfig, str]) -> str:
        prompt_parts: List[str] = []

        tools_section = (
            "### Your Tools\n"
            "To accomplish your goal, you have access to the following tools. You should use them as needed.\n"
            "{{tools}}"
        )

        if prompt_aliases:
            role_and_goal = (
                "You are the coordinator of a team of specialist agents and sub-teams. Your primary goal is to "
                "achieve the following objective by delegating tasks to your team members:\n"
                f"### Goal\n{context.config.description}"
            )
            prompt_parts.append(role_and_goal)
            
            team_lines = []
            for node, alias in prompt_aliases.items():
                node_def = node.node_definition
                if node.is_sub_team and isinstance(node_def, AgentTeamConfig):
                    # For sub-teams, use its role and description
                    role = node_def.role or "(Sub-Team)"
                    team_lines.append(f"- **{alias}** (Role: {role}): {node_def.description}")
                elif isinstance(node_def, AgentConfig):
                    # For agents, use its role and description
                    team_lines.append(f"- **{alias}** (Role: {node_def.role}): {node_def.description}")

            team_manifest = "### Your Team\n" + "\n".join(team_lines)
            prompt_parts.append(team_manifest)

            rules_list: List[str] = []
            for node, alias in prompt_aliases.items():
                if node.dependencies:
                    dep_names = [prompt_aliases.get(dep, dep.name) for dep in node.dependencies]
                    rules_list.append(f"To use '{alias}', you must have already successfully used: {', '.join(f'`{name}`' for name in dep_names)}.")
            
            if rules_list:
                rules_section = "### Execution Rules\n" + "\n".join(rules_list)
                prompt_parts.append(rules_section)

            prompt_parts.append(tools_section)
                
            final_instruction = "### Your Task\nAnalyze the user's request, formulate a plan, and use the `SendMessageTo` tool to delegate tasks to your team. Address team members by their unique ID as listed under 'Your Team'."
            prompt_parts.append(final_instruction)
        else:
            role_and_goal = (
                "You are working alone. Your primary goal is to achieve the following objective:\n"
                f"### Goal\n{context.config.description}"
            )
            prompt_parts.append(role_and_goal)
            prompt_parts.append("### Your Team\nYou are working alone on this task.")
            prompt_parts.append(tools_section)
            final_instruction = "### Your Task\nAnalyze the user's request, formulate a plan, and use your available tools to achieve the goal."
            prompt_parts.append(final_instruction)

        return "\n\n".join(prompt_parts)
