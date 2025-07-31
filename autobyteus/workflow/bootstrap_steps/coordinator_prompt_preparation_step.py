# file: autobyteus/autobyteus/workflow/bootstrap_steps/coordinator_prompt_preparation_step.py
import logging
from typing import TYPE_CHECKING, Dict, Set, List

from autobyteus.workflow.bootstrap_steps.base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.workflow.context.workflow_node_config import WorkflowNodeConfig
from autobyteus.workflow.context.workflow_config import WorkflowConfig

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class CoordinatorPromptPreparationStep(BaseWorkflowBootstrapStep):
    """
    Bootstrap step to dynamically generate the coordinator's system prompt
    based on the workflow's structure and store it in the workflow's state.
    """
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing CoordinatorPromptPreparationStep.")
        try:
            coordinator_node = context.config.coordinator_node
            member_nodes = {node for node in context.config.nodes if node != coordinator_node}

            member_node_ids = self._generate_unique_node_ids(member_nodes)
            dynamic_prompt = self._generate_prompt(context, member_node_ids)
            
            context.state.prepared_coordinator_prompt = dynamic_prompt

            logger.info(f"Workflow '{workflow_id}': Coordinator prompt prepared successfully and stored in state.")
            return True
        except Exception as e:
            logger.error(f"Workflow '{workflow_id}': Failed to prepare coordinator prompt: {e}", exc_info=True)
            return False

    def _generate_unique_node_ids(self, member_nodes: Set[WorkflowNodeConfig]) -> Dict[WorkflowNodeConfig, str]:
        id_map: Dict[WorkflowNodeConfig, str] = {}
        name_counts: Dict[str, int] = {}
        sorted_nodes = sorted(list(member_nodes), key=lambda n: n.name)
        for node in sorted_nodes:
            base_name = node.name
            count = name_counts.get(base_name, 0)
            unique_id = f"{base_name}_{count + 1}" if base_name in name_counts else base_name
            id_map[node] = unique_id
            name_counts[base_name] = count + 1
        return id_map

    def _generate_prompt(self, context: 'WorkflowContext', member_node_ids: Dict[WorkflowNodeConfig, str]) -> str:
        prompt_parts: List[str] = []

        tools_section = (
            "### Your Tools\n"
            "To accomplish your goal, you have access to the following tools. You should use them as needed.\n"
            "{{tools}}"
        )

        if member_node_ids:
            role_and_goal = (
                "You are the coordinator of a team of specialist agents and sub-workflows. Your primary goal is to "
                "achieve the following objective by delegating tasks to your team members:\n"
                f"### Goal\n{context.config.description}"
            )
            prompt_parts.append(role_and_goal)
            
            team_lines = []
            for node, uid in member_node_ids.items():
                node_def = node.node_definition
                if node.is_subworkflow and isinstance(node_def, WorkflowConfig):
                    # For sub-workflows, use its role and description
                    role = node_def.role or "(Sub-Workflow)"
                    team_lines.append(f"- **{uid}** (Role: {role}): {node_def.description}")
                elif isinstance(node_def, AgentConfig):
                    # For agents, use its role and description
                    team_lines.append(f"- **{uid}** (Role: {node_def.role}): {node_def.description}")

            team_manifest = "### Your Team\n" + "\n".join(team_lines)
            prompt_parts.append(team_manifest)

            rules_list: List[str] = []
            for node, uid in member_node_ids.items():
                if node.dependencies:
                    dep_names = [member_node_ids.get(dep, dep.name) for dep in node.dependencies]
                    rules_list.append(f"To use '{uid}', you must have already successfully used: {', '.join(f'`{name}`' for name in dep_names)}.")
            
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

