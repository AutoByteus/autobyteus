# file: autobyteus/autobyteus/agent_team/bootstrap_steps/agent_tool_injection_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent.context import AgentConfig
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.tools.registry import default_tool_registry
from autobyteus.task_management.tools import (
    GetTaskBoardStatus,
    PublishTaskPlan,
    UpdateTaskStatus,
)

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class AgentToolInjectionStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to prepare the final, immutable configuration for every
    agent in the team. It injects team-aware tools and shared context.
    This step runs eagerly at startup to allow for early validation and
    predictable behavior.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing AgentToolInjectionStep to prepare all agent configurations.")
        
        team_manager = context.team_manager
        if not team_manager:
            logger.error(f"Team '{team_id}': TeamManager not found in context. Cannot inject tools.")
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

                # --- THE FIX ---
                # The shared context is injected into the initial_custom_data dictionary,
                # which is then used by the AgentFactory to create the AgentRuntimeState.
                if final_config.initial_custom_data is None:
                    final_config.initial_custom_data = {}
                final_config.initial_custom_data["team_context"] = context
                logger.debug(f"Team '{team_id}': Injected shared team_context into initial_custom_data for agent '{unique_name}'.")

                # --- Tool Injection ---
                tools_to_add = final_config.tools[:]

                send_message_tool = default_tool_registry.create_tool(SendMessageTo.get_name())
                if isinstance(send_message_tool, SendMessageTo):
                    send_message_tool.set_team_manager(team_manager)
                tools_to_add.append(send_message_tool)

                if node_config_wrapper == coordinator_node_config:
                    # Coordinator gets planning and monitoring tools
                    tools_to_add.append(default_tool_registry.create_tool(PublishTaskPlan.get_name()))
                    tools_to_add.append(default_tool_registry.create_tool(GetTaskBoardStatus.get_name()))
                    
                    # Apply coordinator prompt prepared in a previous step
                    coordinator_prompt = context.state.prepared_coordinator_prompt
                    if coordinator_prompt:
                        final_config.system_prompt = coordinator_prompt
                        logger.info(f"Team '{team_id}': Applied dynamic prompt to coordinator '{unique_name}'.")
                else:
                    # Member agents get task execution and artifact management tools
                    tools_to_add.append(default_tool_registry.create_tool(GetTaskBoardStatus.get_name()))
                    tools_to_add.append(default_tool_registry.create_tool(UpdateTaskStatus.get_name()))

                # Remove duplicates by converting to a set based on tool name, then back to list
                final_config.tools = list({tool.get_name(): tool for tool in tools_to_add}.values())
                
                # Store the final, ready-to-use config in the team's state
                context.state.final_agent_configs[unique_name] = final_config
                logger.info(f"Team '{team_id}': Prepared final config for agent '{unique_name}' with tools: {[t.get_name() for t in final_config.tools]}")
            
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Failed during agent configuration preparation: {e}", exc_info=True)
            return False
