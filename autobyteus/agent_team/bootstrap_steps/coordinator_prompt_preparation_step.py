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
    It now assumes all node names are unique.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing CoordinatorPromptPreparationStep.")
        try:
            # The prompt is generated and stored in the state for the TeamManager to apply later.
            dynamic_prompt = self._generate_prompt(context)
            context.state.prepared_coordinator_prompt = dynamic_prompt

            logger.info(f"Team '{team_id}': Coordinator prompt prepared successfully and stored in state.")
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Failed to prepare coordinator prompt: {e}", exc_info=True)
            return False

    def _generate_prompt(self, context: 'AgentTeamContext') -> str:
        """Generates the coordinator's prompt using the unique names of the team members."""
        prompt_parts: List[str] = []
        coordinator_node = context.config.coordinator_node
        member_nodes = {node for node in context.config.nodes if node != coordinator_node}

        tools_section = (
            "### Your Tools\n"
            "To accomplish your goal, you have access to the following tools. You should use them as needed.\n"
            "{{tools}}"
        )

        if member_nodes:
            role_and_goal = (
                "You are the coordinator of a team of specialist agents. Your primary goal is to achieve the user's objective by planning and delegating tasks to your team members.\n"
                f"### Goal\n{context.config.description}"
            )
            prompt_parts.append(role_and_goal)
            
            team_lines = []
            # Sort for deterministic prompt generation
            for node in sorted(list(member_nodes), key=lambda n: n.name):
                node_def = node.node_definition
                team_lines.append(f"- name: {node.name} description: {node_def.description}")

            team_manifest = "### Your Team\n" + "\n".join(team_lines)
            prompt_parts.append(team_manifest)

            # THE FIX: Add the "Mission Workflow" section as intended.
            mission_workflow = (
                "### Your Mission Workflow\n"
                "To succeed, you must follow this workflow:\n"
                "1.  **Analyze and Plan**: Carefully analyze the user's request. Decompose it into a logical, step-by-step plan. For each step, define a clear task, determine which team member is best suited to perform it, and note any dependencies on other tasks.\n"
                "2.  **Publish the Plan**: Use the `PublishTaskPlan` tool to submit your complete plan to the team's shared task board. This is a critical step that makes the plan official.\n"
                "3.  **Delegate and Inform**: Use the `SendMessageTo` tool to notify each team member that they have been assigned a new task. The message should be a simple notification, for example: 'You have a new task, please check the task board for details.' Do NOT include task details in the message itself.\n"
                "4.  **Monitor and Adapt**: Use the `GetTaskBoardStatus` tool to monitor the team's progress. If tasks get stuck or fail, coordinate with your team to resolve the issues and adapt the plan if necessary."
            )
            prompt_parts.append(mission_workflow)

            rules_list: List[str] = [
                "You MUST address team members by their unique 'name' when using the `SendMessageTo` tool."
            ]
            for node in sorted(list(member_nodes), key=lambda n: n.name):
                if node.dependencies:
                    dep_names = [dep.name for dep in node.dependencies]
                    rules_list.append(f"To use '{node.name}', you must have already successfully used: {', '.join(f'`{name}`' for name in dep_names)}.")
            
            rules_section = "### Execution Rules\n" + "\n".join(rules_list)
            prompt_parts.append(rules_section)

            prompt_parts.append(tools_section)
                
            final_instruction = (
                "### Your Task\n"
                "Begin by analyzing the user's request below. Formulate a plan according to the Mission Workflow and then use your tools to publish it and delegate the work."
            )
            prompt_parts.append(final_instruction)
        else:
            # Case where coordinator is the only node
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
