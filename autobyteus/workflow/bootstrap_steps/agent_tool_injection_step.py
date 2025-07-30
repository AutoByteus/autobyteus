# file: autobyteus/autobyteus/workflow/bootstrap_steps/agent_tool_injection_step.py
import logging
from typing import TYPE_CHECKING, Dict, Set

from autobyteus.workflow.bootstrap_steps.base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.workflow.context.workflow_node_config import WorkflowNodeConfig
from autobyteus.tools.registry import default_tool_registry

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class AgentToolInjectionStep(BaseWorkflowBootstrapStep):
    """
    Bootstrap step to finalize agent configs by injecting workflow-aware tools
    like SendMessageTo. It also applies the prepared coordinator prompt.
    The final configs are stored in the workflow's runtime state.
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
                modified_config = node.effective_config.copy()

                # --- FIX: Use ToolRegistry to create SendMessageTo tool and inject definition ---
                tool_registry = default_tool_registry
                send_message_tool_instance = tool_registry.create_tool(SendMessageTo.get_name())
                
                if isinstance(send_message_tool_instance, SendMessageTo):
                    send_message_tool_instance.set_team_manager(team_manager)
                else:
                    # This should not happen if the tool is registered correctly.
                    logger.error(f"Failed to create SendMessageTo tool for agent '{friendly_name}'. Tool created was not of the correct type.")
                    return False

                # Remove any existing SendMessageTo instance and add the new one
                modified_config.tools = [t for t in modified_config.tools if not isinstance(t, SendMessageTo)]
                modified_config.tools.append(send_message_tool_instance)
                
                if node == coordinator_node:
                    modified_config.system_prompt = coordinator_prompt

                final_agent_configs[friendly_name] = modified_config

            # Store the resolved configs in the central workflow state.
            context.state.resolved_agent_configs = final_agent_configs

            logger.info(f"Workflow '{workflow_id}': Agent tool injection complete. Final configs populated in WorkflowRuntimeState.")
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
