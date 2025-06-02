# file: autobyteus/autobyteus/agent/handlers/approved_tool_invocation_event_handler.py
import logging
import json
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import ApprovedToolInvocationEvent, ToolResultEvent
from autobyteus.agent.tool_invocation import ToolInvocation

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext

logger = logging.getLogger(__name__)

class ApprovedToolInvocationEventHandler(AgentEventHandler):
    """
    Handles ApprovedToolInvocationEvents by executing the specified tool,
    logging the call, and queueing a ToolResultEvent with the outcome.
    This handler assumes the tool invocation has already been approved.
    """
    def __init__(self):
        logger.info("ApprovedToolInvocationEventHandler initialized.")

    async def handle(self,
                     event: ApprovedToolInvocationEvent,
                     context: 'AgentContext') -> None: # context is composite
        if not isinstance(event, ApprovedToolInvocationEvent):
            logger.warning(f"ApprovedToolInvocationEventHandler received non-ApprovedToolInvocationEvent: {type(event)}. Skipping.")
            return

        tool_invocation: ToolInvocation = event.tool_invocation
        tool_name = tool_invocation.name
        arguments = tool_invocation.arguments
        invocation_id = tool_invocation.id

        agent_id = context.agent_id 
        # MODIFIED: Access tool_interaction_log_queue via context.output_data_queues
        tool_log_queue = context.output_data_queues.tool_interaction_log_queue 

        logger.info(f"Agent '{agent_id}' handling ApprovedToolInvocationEvent for tool: '{tool_name}' (ID: {invocation_id}) with args: {arguments}")

        try:
            args_str = json.dumps(arguments)
        except TypeError:
            args_str = str(arguments)
        log_msg_call = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Arguments: {args_str}"
        # MODIFIED: Use enqueue_tool_interaction_log method
        await context.output_data_queues.enqueue_tool_interaction_log(log_msg_call)

        tool_instance = context.get_tool(tool_name)
        
        result_event: ToolResultEvent

        if not tool_instance:
            error_message = f"Tool '{tool_name}' not found or configured for agent '{agent_id}'."
            logger.error(error_message)
            result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
            context.add_message_to_history({
                "role": "tool",
                "tool_call_id": invocation_id,
                "name": tool_name,
                "content": f"Error: Approved tool '{tool_name}' execution failed. Reason: {error_message}",
            })
            log_msg_error = f"[APPROVED_TOOL_ERROR] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Error: {error_message}"
            # MODIFIED: Use enqueue_tool_interaction_log method
            await context.output_data_queues.enqueue_tool_interaction_log(log_msg_error)
        else:
            try:
                logger.debug(f"Executing approved tool '{tool_name}' for agent '{agent_id}'. Invocation ID: {invocation_id}")
                execution_result = await tool_instance.execute(context=context, **arguments)
                
                try:
                    result_str_for_log = json.dumps(execution_result)
                except TypeError:
                    result_str_for_log = str(execution_result)

                logger.info(f"Approved tool '{tool_name}' (ID: {invocation_id}) executed successfully by agent '{agent_id}'. Result: {result_str_for_log[:200]}...")
                result_event = ToolResultEvent(tool_name=tool_name, result=execution_result, error=None, tool_invocation_id=invocation_id)
                
                history_content = str(execution_result)

                context.add_message_to_history({
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": history_content,
                })
                log_msg_result = f"[APPROVED_TOOL_RESULT] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Outcome (first 200 chars): {result_str_for_log[:200]}"
                # MODIFIED: Use enqueue_tool_interaction_log method
                await context.output_data_queues.enqueue_tool_interaction_log(log_msg_result)

            except Exception as e:
                error_message = f"Error executing approved tool '{tool_name}' (ID: {invocation_id}): {str(e)}"
                logger.error(f"Agent '{agent_id}' {error_message}", exc_info=True)
                result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
                context.add_message_to_history({
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": f"Error: Approved tool '{tool_name}' execution failed. Reason: {error_message}",
                })
                log_msg_exception = f"[APPROVED_TOOL_EXCEPTION] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Exception: {error_message}"
                # MODIFIED: Use enqueue_tool_interaction_log method
                await context.output_data_queues.enqueue_tool_interaction_log(log_msg_exception)
        
        # MODIFIED: Access input_event_queues and its specific enqueue method
        await context.input_event_queues.enqueue_tool_result(result_event)
        logger.debug(f"Agent '{agent_id}' enqueued ToolResultEvent for approved tool '{tool_name}' (ID: {invocation_id}).")
