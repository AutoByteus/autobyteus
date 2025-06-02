# file: autobyteus/autobyteus/agent/bootstrap_steps/tool_initialization_step.py
import logging
from typing import TYPE_CHECKING, Dict

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager
    from autobyteus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

class ToolInitializationStep(BaseBootstrapStep):
    """
    Bootstrap step for initializing the agent's tools.
    """
    def __init__(self, tool_registry: 'ToolRegistry'):
        if tool_registry is None: # pragma: no cover
            raise ValueError("ToolInitializationStep requires a ToolRegistry instance.")
        self.tool_registry = tool_registry
        logger.debug("ToolInitializationStep initialized.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        agent_id = context.agent_id
        phase_manager.notify_initializing_tools()
        logger.info(f"Agent '{agent_id}': Executing ToolInitializationStep.")

        try:
            tool_names = context.definition.tool_names
            custom_tool_configs = context.custom_tool_config

            if not tool_names:
                logger.info(f"Agent '{agent_id}': No tool names defined. Tool initialization skipped.")
                context.state.tool_instances = {}
            else:
                tool_instances_dict: Dict[str, BaseTool] = {}
                logger.debug(f"Agent '{agent_id}': Instantiating tools: {tool_names}")
                for tool_name in tool_names:
                    tool_config_for_tool = custom_tool_configs.get(tool_name) if custom_tool_configs else None
                    try:
                        tool_instance = self.tool_registry.create_tool(tool_name, tool_config_for_tool)
                        tool_instances_dict[tool_name] = tool_instance
                        logger.debug(f"Agent '{agent_id}': Tool '{tool_name}' instantiated successfully.")
                    except Exception as e_tool: # pragma: no cover
                        # Log specific tool creation error but let overall step fail to catch configuration issues
                        logger.error(f"Agent '{agent_id}': Failed to create tool '{tool_name}'. Error: {e_tool}", exc_info=True)
                        raise # Re-raise to be caught by the broader try-except in this method

                context.state.tool_instances = tool_instances_dict
                logger.info(f"Agent '{agent_id}': {len(tool_instances_dict)} tools instantiated and stored: {list(tool_instances_dict.keys())}.")
            return True
        except Exception as e:
            error_message = f"Agent '{agent_id}': Critical failure during tool initialization: {e}"
            logger.error(error_message, exc_info=True)
            # Ensure tool_instances is at least an empty dict if it failed mid-way or before assignment
            if context.state.tool_instances is None:
                 context.state.tool_instances = {}
            await context.input_event_queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
            return False
