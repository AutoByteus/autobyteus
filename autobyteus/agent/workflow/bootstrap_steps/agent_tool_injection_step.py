# file: autobyteus/autobyteus/agent/workflow/bootstrap_steps/agent_tool_injection_step.py
import logging
import copy
from typing import TYPE_CHECKING, Dict, Set

from .base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from ....agent.context import AgentConfig
from ....agent.message.send_message_to import SendMessageTo
from ..context.workflow_node_config import WorkflowNodeConfig

if TYPE_CHECKING:
    from ..context.workflow_context import WorkflowContext
    from ..phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class AgentToolInjectionStep(BaseWorkflowBootstrapStep):
    """
    Bootstrap step to finalize agent configs by injecting workflow-aware tools
    like SendMessageTo. It also applies the prepared coordinator prompt.
    """
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing AgentToolInjectionStep.")
        try:
            team_manager = context.team_manager
            if not team_manager:
                raise RuntimeError("TeamManager must be initialized before this step.")

            coordinator_node = context.config.coordinator_node
            coordinator_prompt = context.state.prepared_coordinator_prompt
            if not coordinator_prompt:
                raise RuntimeError("Coordinator prompt not prepared in a prior step.")
            
            final_agent_configs: Dict[str, AgentConfig] = {}
            
            # Use the same unique ID generation logic as the prompt step for consistency
            member_nodes = {node for node in context.config.nodes if node != coordinator_node}
            node_ids = self._generate_unique_node_ids(member_nodes)
            node_ids[coordinator_node] = coordinator_node.name

            for node, friendly_name in node_ids.items():
                modified_config = copy.deepcopy(node.effective_config)

                has_send_message_tool = any(isinstance(tool, SendMessageTo) for tool in modified_config.tools)
                if not has_send_message_tool:
                    modified_config.tools.append(SendMessageTo(team_manager=team_manager))
                else:
                    modified_config.tools = [
                        tool if not isinstance(tool, SendMessageTo) else SendMessageTo(team_manager=team_manager)
                        for tool in modified_config.tools
                    ]
                
                if node == coordinator_node:
                    modified_config.system_prompt = coordinator_prompt

                final_agent_configs[friendly_name] = modified_config

            team_manager.set_agent_configs(final_agent_configs)

            logger.info(f"Workflow '{workflow_id}': Agent tool injection complete. Final configs populated in TeamManager.")
            return True
        except Exception as e:
            logger.error(f"Workflow '{workflow_id}': Failed during agent tool injection: {e}", exc_info=True)
            return False

    def _generate_unique_node_ids(self, member_nodes: Set[WorkflowNodeConfig]) -> Dict[WorkflowNodeConfig, str]:
        """Helper to generate consistent friendly names for nodes."""
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
