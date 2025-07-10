# file: autobyteus/autobyteus/agent/handlers/approved_tool_invocation_event_handler.py
import logging
import json
import traceback 
from typing import TYPE_CHECKING, Optional 

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import ApprovedToolInvocationEvent, ToolResultEvent
from autobyteus.agent.tool_invocation import ToolInvocation

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 

logger = logging.getLogger(__name__)

class ApprovedToolInvocationEventHandler(AgentEventHandler):
    """
    Handles ApprovedToolInvocationEvents by executing the specified tool,
    emitting AGENT_DATA_TOOL_LOG events for call and result/error,
    and queueing a ToolResultEvent with the outcome.
    This handler assumes the tool invocation has already been approved.
    """
    def __init__(self):
        logger.info("ApprovedToolInvocationEventHandler initialized.")

    async def handle(self,
                     event: ApprovedToolInvocationEvent,
                     context: 'AgentContext') -> None: 
        if not isinstance(event, ApprovedToolInvocationEvent):
            logger.warning(f"ApprovedToolInvocationEventHandler received non-ApprovedToolInvocationEvent: {type(event)}. Skipping.")
            return

        tool_invocation: ToolInvocation = event.tool_invocation
        tool_name = tool_invocation.name
        arguments = tool_invocation.arguments
        invocation_id = tool_invocation.id
        agent_id = context.agent_id 

        notifier: Optional['AgentExternalEventNotifier'] = None
        if context.phase_manager:
            notifier = context.phase_manager.notifier
        
        if not notifier: # pragma: no cover
            logger.error(f"Agent '{agent_id}': Notifier not available in ApprovedToolInvocationEventHandler. Tool interaction logs will not be emitted.")

        logger.info(f"Agent '{agent_id}' handling ApprovedToolInvocationEvent for tool: '{tool_name}' (ID: {invocation_id}) with args: {arguments}")

        try:
            args_str = json.dumps(arguments)
        except TypeError: # pragma: no cover
            args_str = str(arguments) 
        log_msg_call = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Arguments: {args_str}"
        
        if notifier:
            try:
                log_data = {
                    "log_entry": log_msg_call,
                    "tool_invocation_id": invocation_id,
                    "tool_name": tool_name,
                }
                notifier.notify_agent_data_tool_log(log_data)
            except Exception as e_notify: 
                 logger.error(f"Agent '{agent_id}': Error notifying approved tool call log: {e_notify}", exc_info=True)

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
            log_msg_error = f"[APPROVED_TOOL_ERROR] {error_message}"
            if notifier:
                try:
                    # Log entry
                    log_data = { "log_entry": log_msg_error, "tool_invocation_id": invocation_id, "tool_name": tool_name }
                    notifier.notify_agent_data_tool_log(log_data)
                    # Generic output error
                    notifier.notify_agent_error_output_generation(
                        error_source=f"ApprovedToolExecution.ToolNotFound.{tool_name}",
                        error_message=error_message
                    )
                except Exception as e_notify: 
                    logger.error(f"Agent '{agent_id}': Error notifying approved tool error log/output error: {e_notify}", exc_info=True)
        else:
            try:
                logger.debug(f"Executing approved tool '{tool_name}' for agent '{agent_id}'. Invocation ID: {invocation_id}")
                execution_result = await tool_instance.execute(context=context, **arguments)
                
                try:
                    result_json_for_log = json.dumps(execution_result)
                except (TypeError, ValueError): 
                    result_json_for_log = json.dumps(str(execution_result))

                logger.info(f"Approved tool '{tool_name}' (ID: {invocation_id}) executed successfully by agent '{agent_id}'.")
                result_event = ToolResultEvent(tool_name=tool_name, result=execution_result, error=None, tool_invocation_id=invocation_id)
                
                history_content = str(execution_result) 
                context.add_message_to_history({
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": history_content,
                })
                log_msg_result = f"[APPROVED_TOOL_RESULT] {result_json_for_log}"
                if notifier:
                    try:
                        # Log entry with embedded JSON result
                        log_data = { "log_entry": log_msg_result, "tool_invocation_id": invocation_id, "tool_name": tool_name }
                        notifier.notify_agent_data_tool_log(log_data)
                    except Exception as e_notify: 
                        logger.error(f"Agent '{agent_id}': Error notifying approved tool result log: {e_notify}", exc_info=True)

            except Exception as e: 
                error_message = f"Error executing approved tool '{tool_name}' (ID: {invocation_id}): {str(e)}"
                error_details = traceback.format_exc()
                logger.error(f"Agent '{agent_id}' {error_message}", exc_info=True)
                result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
                context.add_message_to_history({
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": f"Error: Approved tool '{tool_name}' execution failed. Reason: {error_message}",
                })
                log_msg_exception = f"[APPROVED_TOOL_EXCEPTION] {error_message}\nDetails:\n{error_details}"
                if notifier:
                    try:
                        # Log entry
                        log_data = { "log_entry": log_msg_exception, "tool_invocation_id": invocation_id, "tool_name": tool_name }
                        notifier.notify_agent_data_tool_log(log_data)
                        # Generic output error
                        notifier.notify_agent_error_output_generation(
                            error_source=f"ApprovedToolExecution.Exception.{tool_name}",
                            error_message=error_message,
                            error_details=error_details
                        )
                    except Exception as e_notify: 
                        logger.error(f"Agent '{agent_id}': Error notifying approved tool exception log/output error: {e_notify}", exc_info=True)
        
        await context.input_event_queues.enqueue_tool_result(result_event)
        logger.debug(f"Agent '{agent_id}' enqueued ToolResultEvent for approved tool '{tool_name}' (ID: {invocation_id}).")
