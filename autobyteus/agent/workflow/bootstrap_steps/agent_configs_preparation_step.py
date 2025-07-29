# file: autobyteus/autobyteus/agent/workflow/bootstrap_steps/agent_configs_preparation_step.py
import logging
import copy
from typing import TYPE_CHECKING, Dict, Set, List

from .base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from ....agent.context import AgentConfig
from ..context.workflow_node_config import WorkflowNodeConfig
from ....agent.message.send_message_to import SendMessageTo

if TYPE_CHECKING:
    from ..context.workflow_context import WorkflowContext
    from ..phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class AgentConfigsPreparationStep(BaseWorkflowBootstrapStep):
    """
    Bootstrap step to dynamically prepare the final AgentConfig for every agent
    in the workflow. This includes generating the coordinator's dynamic prompt and
    injecting workflow-aware tools like SendMessageTo.
    """
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing AgentConfigsPreparationStep.")
        try:
            team_manager = context.team_manager
            if not team_manager:
                raise RuntimeError("TeamManager must be initialized before this step.")

            coordinator_node = context.config.coordinator_node
            member_nodes = {node for node in context.config.nodes if node != coordinator_node}

            member_node_ids = self._generate_unique_node_ids(member_nodes)
            coordinator_prompt = self._generate_prompt(context, member_node_ids)
            
            final_agent_configs: Dict[str, AgentConfig] = {}
            
            # Prepare all configs
            all_node_ids = member_node_ids.copy()
            all_node_ids[coordinator_node] = coordinator_node.name

            for node, friendly_name in all_node_ids.items():
                # 1. Create a deep copy to avoid modifying original user config
                modified_config = copy.deepcopy(node.effective_config)

                # 2. Inject SendMessageTo tool with the TeamManager instance
                has_send_message_tool = any(isinstance(tool, SendMessageTo) for tool in modified_config.tools)
                if not has_send_message_tool:
                    modified_config.tools.append(SendMessageTo(team_manager=team_manager))
                else:
                    # Replace existing instance to ensure correct TeamManager is injected
                    modified_config.tools = [
                        tool if not isinstance(tool, SendMessageTo) else SendMessageTo(team_manager=team_manager)
                        for tool in modified_config.tools
                    ]
                
                # 3. For coordinator, set the dynamic prompt
                if node == coordinator_node:
                    modified_config.system_prompt = coordinator_prompt

                final_agent_configs[friendly_name] = modified_config

            # 4. Populate the TeamManager with the final configs
            team_manager.set_agent_configs(final_agent_configs)

            logger.info(f"Workflow '{workflow_id}': All agent configurations prepared and populated in TeamManager.")
            return True
        except Exception as e:
            logger.error(f"Workflow '{workflow_id}': Failed to prepare agent configs: {e}", exc_info=True)
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

        if member_node_ids:
            role_and_goal = (
                "You are the coordinator of a team of specialist agents. Your primary goal is to achieve the "
                "following objective by delegating tasks to your team members:\n"
                f"### Goal\n{context.config.description}"
            )
            prompt_parts.append(role_and_goal)
            
            team_lines = [f"- **{uid}** (Role: {node.effective_config.role}): {node.effective_config.description}" for node, uid in member_node_ids.items()]
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
                
            final_instruction = "### Your Task\nAnalyze the user's request, formulate a plan, and use the `SendMessageTo` tool to delegate tasks to your team. Address team members by their unique ID as listed under 'Your Team'."
            prompt_parts.append(final_instruction)
        else:
            role_and_goal = (
                "You are working alone. Your primary goal is to achieve the following objective:\n"
                f"### Goal\n{context.config.description}"
            )
            prompt_parts.append(role_and_goal)
            prompt_parts.append("### Your Team\nYou are working alone on this task.")
            final_instruction = "### Your Task\nAnalyze the user's request, formulate a plan, and use your available tools to achieve the goal."
            prompt_parts.append(final_instruction)

        return "\n\n".join(prompt_parts)
