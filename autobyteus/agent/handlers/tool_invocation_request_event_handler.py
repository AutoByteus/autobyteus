# file: autobyteus/autobyteus/agent/handlers/tool_invocation_request_event_handler.py
import logging
import json 
import traceback 
from typing import TYPE_CHECKING, Optional 

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import PendingToolInvocationEvent, ToolResultEvent 
from autobyteus.agent.tool_invocation import ToolInvocation

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 

logger = logging.getLogger(__name__)

class ToolInvocationRequestEventHandler(AgentEventHandler):
    """
    Handles PendingToolInvocationEvents.
    If 'auto_execute_tools' (from AgentConfig) is False, it stores the invocation,
    updates history, and emits an AGENT_REQUEST_TOOL_INVOCATION_APPROVAL event via the notifier.
    If 'auto_execute_tools' is True, it executes the tool directly, emits
    AGENT_DATA_TOOL_LOG events for call and result/error, 
    and queues a ToolResultEvent.
    """
    def __init__(self): # pragma: no cover
        logger.info("ToolInvocationRequestEventHandler initialized.")

    async def _execute_tool_directly(self, 
                                     tool_invocation: ToolInvocation, 
                                     context: 'AgentContext',
                                     notifier: Optional['AgentExternalEventNotifier']) -> None: # pragma: no cover
        agent_id = context.agent_id 
        tool_name = tool_invocation.name
        arguments = tool_invocation.arguments
        invocation_id = tool_invocation.id

        if notifier:
            try:
                auto_exec_data = {
                    "invocation_id": invocation_id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                }
                notifier.notify_agent_tool_invocation_auto_executing(auto_exec_data)
            except Exception as e_notify:
                logger.error(f"Agent '{agent_id}': Error notifying tool auto-execution: {e_notify}", exc_info=True)
        
        logger.info(f"Agent '{agent_id}' executing tool directly: '{tool_name}' (ID: {invocation_id}) with args: {arguments}")
        
        try:
            args_str = json.dumps(arguments)
        except TypeError:
            args_str = str(arguments) 

        log_msg_call = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Arguments: {args_str}"
        if notifier:
            try:
                log_data = {
                    "log_entry": log_msg_call,
                    "tool_invocation_id": invocation_id,
                    "tool_name": tool_name,
                }
                notifier.notify_agent_data_tool_log(log_data)
            except Exception as e_notify: 
                 logger.error(f"Agent '{agent_id}': Error notifying tool call log: {e_notify}", exc_info=True)

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
                "content": f"Error: Tool '{tool_name}' execution failed. Reason: {error_message}",
            })
            log_msg_error = f"[TOOL_ERROR_DIRECT] {error_message}"
            if notifier:
                try:
                    # Log entry
                    log_data = { "log_entry": log_msg_error, "tool_invocation_id": invocation_id, "tool_name": tool_name, }
                    notifier.notify_agent_data_tool_log(log_data)
                    # Generic output error
                    notifier.notify_agent_error_output_generation(
                        error_source=f"ToolExecutionDirect.ToolNotFound.{tool_name}",
                        error_message=error_message
                    )
                except Exception as e_notify: 
                    logger.error(f"Agent '{agent_id}': Error notifying tool error log/output error: {e_notify}", exc_info=True)
        else:
            try:
                logger.debug(f"Executing tool '{tool_name}' for agent '{agent_id}'. Invocation ID: {invocation_id}")
                execution_result = await tool_instance.execute(context=context, **arguments) 
                
                try:
                    result_json_for_log = json.dumps(execution_result)
                except (TypeError, ValueError): 
                    result_json_for_log = json.dumps(str(execution_result))

                logger.info(f"Tool '{tool_name}' (ID: {invocation_id}) executed by agent '{agent_id}'.")
                result_event = ToolResultEvent(tool_name=tool_name, result=execution_result, error=None, tool_invocation_id=invocation_id)
                
                history_content = str(execution_result) 
                context.add_message_to_history({ 
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": history_content,
                })
                log_msg_result = f"[TOOL_RESULT_DIRECT] {result_json_for_log}"
                if notifier:
                    try:
                        # Log entry with embedded JSON result
                        log_data = { "log_entry": log_msg_result, "tool_invocation_id": invocation_id, "tool_name": tool_name }
                        notifier.notify_agent_data_tool_log(log_data)
                    except Exception as e_notify: 
                        logger.error(f"Agent '{agent_id}': Error notifying tool result log: {e_notify}", exc_info=True)

            except Exception as e: 
                error_message = f"Error executing tool '{tool_name}' (ID: {invocation_id}): {str(e)}"
                error_details = traceback.format_exc()
                logger.error(f"Agent '{agent_id}' {error_message}", exc_info=True)
                result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
                context.add_message_to_history({ 
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": f"Error: Tool '{tool_name}' execution failed. Reason: {error_message}",
                })
                log_msg_exception = f"[TOOL_EXCEPTION_DIRECT] {error_message}\nDetails:\n{error_details}"
                if notifier:
                    try:
                        # Log entry
                        log_data = { "log_entry": log_msg_exception, "tool_invocation_id": invocation_id, "tool_name": tool_name }
                        notifier.notify_agent_data_tool_log(log_data)
                        # Generic output error
                        notifier.notify_agent_error_output_generation(
                            error_source=f"ToolExecutionDirect.Exception.{tool_name}",
                            error_message=error_message,
                            error_details=error_details
                        )
                    except Exception as e_notify: 
                        logger.error(f"Agent '{agent_id}': Error notifying tool exception log/output error: {e_notify}", exc_info=True)
        
        await context.input_event_queues.enqueue_tool_result(result_event) 
        logger.debug(f"Agent '{agent_id}' enqueued ToolResultEvent (direct exec) for '{tool_name}' (ID: {invocation_id}).")


    async def handle(self,
                     event: PendingToolInvocationEvent, 
                     context: 'AgentContext') -> None: # pragma: no cover
        if not isinstance(event, PendingToolInvocationEvent): 
            logger.warning(f"ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent: {type(event)}. Skipping.")
            return

        tool_invocation: ToolInvocation = event.tool_invocation
        agent_id = context.agent_id 
        
        notifier: Optional['AgentExternalEventNotifier'] = None
        if context.phase_manager:
            notifier = context.phase_manager.notifier
        
        if not notifier:
            logger.error(f"Agent '{agent_id}': Notifier not available in ToolInvocationRequestEventHandler. Output events for tool approval/logging will be lost.")
            if not context.auto_execute_tools:
                logger.critical(f"Agent '{agent_id}': Notifier is REQUIRED for manual tool approval flow but is unavailable. Tool '{tool_invocation.name}' cannot be processed for approval.")
                return

        if not context.auto_execute_tools:
            logger.info(f"Agent '{agent_id}': Tool '{tool_invocation.name}' (ID: {tool_invocation.id}) requires approval. Storing pending invocation and emitting request.")
            
            context.store_pending_tool_invocation(tool_invocation) 

            try:
                arguments_json_str = json.dumps(tool_invocation.arguments or {})
            except TypeError: 
                logger.warning(f"Could not serialize args for history tool_call for '{tool_invocation.name}'. Using empty dict string.")
                arguments_json_str = "{}"

            context.add_message_to_history({ 
                "role": "assistant",
                "content": None, 
                "tool_calls": [{
                    "id": tool_invocation.id,
                    "type": "function", 
                    "function": {
                        "name": tool_invocation.name,
                        "arguments": arguments_json_str 
                    }
                }]
            })
            
            approval_data = {
                "invocation_id": tool_invocation.id,
                "tool_name": tool_invocation.name,
                "arguments": tool_invocation.arguments,
            }
            if notifier:
                try:
                    notifier.notify_agent_request_tool_invocation_approval(approval_data)
                    logger.debug(f"Agent '{agent_id}': Emitted AGENT_REQUEST_TOOL_INVOCATION_APPROVAL for '{tool_invocation.name}' (ID: {tool_invocation.id}).")
                except Exception as e_notify: 
                    logger.error(f"Agent '{agent_id}': Error emitting AGENT_REQUEST_TOOL_INVOCATION_APPROVAL: {e_notify}", exc_info=True)
            
        else: 
            logger.info(f"Agent '{agent_id}': Tool '{tool_invocation.name}' (ID: {tool_invocation.id}) executing automatically (auto_execute_tools=True).")
            await self._execute_tool_directly(tool_invocation, context, notifier)
