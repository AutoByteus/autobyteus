# file: autobyteus/autobyteus/agent/handlers/create_tool_instances_event_handler.py
import logging
from typing import TYPE_CHECKING, Dict

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import CreateToolInstancesEvent, ProcessSystemPromptEvent, AgentErrorEvent
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

class CreateToolInstancesEventHandler(AgentEventHandler):
    """
    Handles the CreateToolInstancesEvent. This handler is responsible for:
    1. Retrieving tool names from the agent's definition.
    2. Retrieving custom tool configurations from the agent's config.
    3. Instantiating the tools using a ToolRegistry.
    4. Storing the instantiated tools in the agent's runtime state.
    5. Enqueuing a ProcessSystemPromptEvent to continue the agent initialization sequence.
    """

    def __init__(self, tool_registry: 'ToolRegistry'):
        if tool_registry is None:
            raise ValueError("CreateToolInstancesEventHandler requires a ToolRegistry instance.")
        self.tool_registry = tool_registry
        logger.info("CreateToolInstancesEventHandler initialized.")

    async def handle(self,
                     event: CreateToolInstancesEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, CreateToolInstancesEvent):
            logger.warning(f"CreateToolInstancesEventHandler received non-CreateToolInstancesEvent: {type(event)}. Skipping.")
            return

        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Handling CreateToolInstancesEvent.")

        try:
            tool_names = context.definition.tool_names
            custom_tool_configs = context.custom_tool_config # Uses convenience property on AgentContext

            if not tool_names:
                logger.info(f"Agent '{agent_id}': No tool names defined. Skipping tool instantiation. Tool instances will be empty.")
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
                    except Exception as e_tool:
                        logger.error(f"Agent '{agent_id}': Failed to create tool '{tool_name}'. Error: {e_tool}", exc_info=True)
                        # For now, skip this tool and log. Agent initialization will proceed.
                        # If a tool is critical, this might need adjustment or a more specific error.
                
                context.state.tool_instances = tool_instances_dict
                logger.info(f"Agent '{agent_id}': {len(tool_instances_dict)} tools instantiated and stored in state: {list(tool_instances_dict.keys())}.")

            # Enqueue the next event in the initialization sequence
            await context.queues.enqueue_internal_system_event(ProcessSystemPromptEvent())
            logger.debug(f"Agent '{agent_id}': Enqueued ProcessSystemPromptEvent after tool instantiation.")

        except Exception as e:
            error_message = f"Agent '{agent_id}': Failed during tool instantiation phase: {e}"
            logger.error(error_message, exc_info=True)
            # Ensure tool_instances is at least an empty dict on error if partial success not handled above
            if context.state.tool_instances is None: # Should be set to {} or a dict by logic above
                context.state.tool_instances = {}
            await context.queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
