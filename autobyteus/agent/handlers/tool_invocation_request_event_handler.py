# file: autobyteus/autobyteus/agent/handlers/tool_invocation_request_event_handler.py
import logging
import json 
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import PendingToolInvocationEvent, ToolResultEvent 
from autobyteus.agent.tool_invocation import ToolInvocation

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

TOOL_APPROVAL_REQUESTED_EVENT_TYPE = "tool_approval_requested"

class ToolInvocationRequestEventHandler(AgentEventHandler):
    """
    Handles PendingToolInvocationEvents.
    If the agent context's 'auto_execute_tools' flag is False, this handler will
    store the invocation, emit an external event to request approval, and update history.
    Otherwise (if 'auto_execute_tools' is True), it executes the tool directly,
    logs interactions, and queues a ToolResultEvent.
    """
    def __init__(self):
        logger.info("ToolInvocationRequestEventHandler initialized.")

    async def _execute_tool_directly(self, tool_invocation: ToolInvocation, context: 'AgentContext') -> None:
        tool_name = tool_invocation.name
        arguments = tool_invocation.arguments
        invocation_id = tool_invocation.id

        tool_log_queue = context.queues.tool_interaction_log_queue

        logger.info(f"Agent '{context.agent_id}' executing tool directly: '{tool_name}' (ID: {invocation_id}) with args: {arguments}")
        
        try:
            args_str = json.dumps(arguments)
        except TypeError:
            args_str = str(arguments)
        log_msg_call = f"[TOOL_CALL_DIRECT] Agent_ID: {context.agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Arguments: {args_str}"
        await tool_log_queue.put(log_msg_call)

        tool_instance = context.get_tool(tool_name)
        result_event: ToolResultEvent

        if not tool_instance:
            error_message = f"Tool '{tool_name}' not found or configured for agent '{context.agent_id}'."
            logger.error(error_message)
            result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
            context.add_message_to_history({
                "role": "tool",
                "tool_call_id": invocation_id,
                "name": tool_name,
                "content": f"Error: Tool '{tool_name}' execution failed. Reason: {error_message}",
            })
            log_msg_error = f"[TOOL_ERROR_DIRECT] Agent_ID: {context.agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Error: {error_message}"
            await tool_log_queue.put(log_msg_error)
        else:
            try:
                logger.debug(f"Executing tool '{tool_name}' for agent '{context.agent_id}'. Invocation ID: {invocation_id}")
                # Pass AgentContext as a keyword argument to tool_instance.execute
                execution_result = await tool_instance.execute(context=context, **arguments)
                
                try:
                    result_str_for_log = json.dumps(execution_result)
                except TypeError:
                    result_str_for_log = str(execution_result)

                logger.info(f"Tool '{tool_name}' (ID: {invocation_id}) executed successfully by agent '{context.agent_id}'. Result: {result_str_for_log[:200]}...")
                result_event = ToolResultEvent(tool_name=tool_name, result=execution_result, error=None, tool_invocation_id=invocation_id)
                
                history_content = str(execution_result)
                context.add_message_to_history({
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": history_content,
                })
                log_msg_result = f"[TOOL_RESULT_DIRECT] Agent_ID: {context.agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Outcome (first 200 chars): {result_str_for_log[:200]}"
                await tool_log_queue.put(log_msg_result)

            except Exception as e:
                error_message = f"Error executing tool '{tool_name}' (ID: {invocation_id}): {str(e)}"
                logger.error(f"Agent '{context.agent_id}' {error_message}", exc_info=True)
                result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
                context.add_message_to_history({
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": f"Error: Tool '{tool_name}' execution failed. Reason: {error_message}",
                })
                log_msg_exception = f"[TOOL_EXCEPTION_DIRECT] Agent_ID: {context.agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Exception: {error_message}"
                await tool_log_queue.put(log_msg_exception)
        
        await context.queues.enqueue_tool_result(result_event)
        logger.debug(f"Agent '{context.agent_id}' enqueued ToolResultEvent following direct execution of tool '{tool_name}' (ID: {invocation_id}).")


    async def handle(self,
                     event: PendingToolInvocationEvent, 
                     context: 'AgentContext') -> None:
        if not isinstance(event, PendingToolInvocationEvent): 
            logger.warning(f"ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent: {type(event)}. Skipping.")
            return

        tool_invocation: ToolInvocation = event.tool_invocation
        
        # Check tool execution mode from AgentContext.
        # If auto_execute_tools is False, then approval is required.
        if not context.auto_execute_tools:
            logger.info(f"Agent '{context.agent_id}': Tool invocation for '{tool_invocation.name}' (ID: {tool_invocation.id}) requires approval (context.auto_execute_tools=False).")
            
            context.store_pending_tool_invocation(tool_invocation)

            try:
                # Ensure emitter is available. Accessing status_manager which holds emitter.
                # This assumes AgentRuntime correctly sets up AgentStatusManager with itself (an EventEmitter)
                emitter = getattr(context, 'status_manager', None)
                if emitter and hasattr(emitter, 'emitter') and emitter.emitter: # Check if status_manager has an emitter
                    emitter.emitter.emit( # Call emit on the actual emitter instance
                        event_type=TOOL_APPROVAL_REQUESTED_EVENT_TYPE,
                        agent_id=context.agent_id,
                        tool_invocation_id=tool_invocation.id,
                        tool_name=tool_invocation.name,
                        arguments=tool_invocation.arguments,
                        message=f"Agent '{context.agent_id}' requests approval to execute tool '{tool_invocation.name}'."
                    )
                    logger.info(f"Agent '{context.agent_id}': Emitted '{TOOL_APPROVAL_REQUESTED_EVENT_TYPE}' for tool '{tool_invocation.name}' (ID: {tool_invocation.id}).")
                else: # context.status_manager.emitter might be the direct emitter if status_manager is the emitter
                    if hasattr(context, 'status_manager') and hasattr(context.status_manager, 'emit'):
                         context.status_manager.emit(
                            event_type=TOOL_APPROVAL_REQUESTED_EVENT_TYPE,
                            agent_id=context.agent_id,
                            tool_invocation_id=tool_invocation.id,
                            tool_name=tool_invocation.name,
                            arguments=tool_invocation.arguments,
                            message=f"Agent '{context.agent_id}' requests approval to execute tool '{tool_invocation.name}'."
                         )
                         logger.info(f"Agent '{context.agent_id}': Emitted '{TOOL_APPROVAL_REQUESTED_EVENT_TYPE}' via context.status_manager for tool '{tool_invocation.name}' (ID: {tool_invocation.id}).")
                    else:
                        logger.error(f"Agent '{context.agent_id}': Cannot emit tool approval request. Emitter not available via context.status_manager or context.status_manager.emitter.")


            except Exception as e:
                logger.error(f"Agent '{context.agent_id}': Failed to emit '{TOOL_APPROVAL_REQUESTED_EVENT_TYPE}': {e}", exc_info=True)

            try:
                arguments_json_str = json.dumps(tool_invocation.arguments or {})
            except TypeError:
                logger.warning(f"Could not serialize arguments for tool_call history message for tool '{tool_invocation.name}'. Using empty object string.")
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
            logger.debug(f"Agent '{context.agent_id}': Added assistant tool_calls message to history for pending approval of '{tool_invocation.name}' (ID: {tool_invocation.id}).")
        else: # auto_execute_tools is True, proceed with direct execution
            logger.info(f"Agent '{context.agent_id}': Tool invocation for '{tool_invocation.name}' (ID: {tool_invocation.id}) will be executed automatically (context.auto_execute_tools=True).")
            await self._execute_tool_directly(tool_invocation, context)
