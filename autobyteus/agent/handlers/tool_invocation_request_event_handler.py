# file: autobyteus/autobyteus/agent/handlers/tool_invocation_request_event_handler.py
import logging
import json 
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import PendingToolInvocationEvent, ToolResultEvent 
from autobyteus.agent.tool_invocation import ToolInvocation

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext

logger = logging.getLogger(__name__)

# TOOL_APPROVAL_REQUESTED_EVENT_TYPE is removed as external emission is removed

class ToolInvocationRequestEventHandler(AgentEventHandler):
    """
    Handles PendingToolInvocationEvents.
    If 'auto_execute_tools' (from AgentConfig) is False, it stores the invocation 
    and updates history. The responsibility to notify external systems for approval
    is now outside this handler.
    If 'auto_execute_tools' is True, it executes the tool directly, logs, 
    and queues a ToolResultEvent.
    """
    def __init__(self):
        logger.info("ToolInvocationRequestEventHandler initialized.")

    async def _execute_tool_directly(self, tool_invocation: ToolInvocation, context: 'AgentContext') -> None:
        agent_id = context.agent_id # Convenience property
        tool_name = tool_invocation.name
        arguments = tool_invocation.arguments
        invocation_id = tool_invocation.id

        tool_log_queue = context.queues.tool_interaction_log_queue # Convenience property

        logger.info(f"Agent '{agent_id}' executing tool directly: '{tool_name}' (ID: {invocation_id}) with args: {arguments}")
        
        try:
            args_str = json.dumps(arguments)
        except TypeError:
            args_str = str(arguments)
        log_msg_call = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Arguments: {args_str}"
        await tool_log_queue.put(log_msg_call)

        tool_instance = context.get_tool(tool_name) # Convenience property
        result_event: ToolResultEvent

        if not tool_instance:
            error_message = f"Tool '{tool_name}' not found or configured for agent '{agent_id}'."
            logger.error(error_message)
            result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
            context.add_message_to_history({ # Convenience method
                "role": "tool",
                "tool_call_id": invocation_id,
                "name": tool_name,
                "content": f"Error: Tool '{tool_name}' execution failed. Reason: {error_message}",
            })
            log_msg_error = f"[TOOL_ERROR_DIRECT] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Error: {error_message}"
            await tool_log_queue.put(log_msg_error)
        else:
            try:
                logger.debug(f"Executing tool '{tool_name}' for agent '{agent_id}'. Invocation ID: {invocation_id}")
                execution_result = await tool_instance.execute(context=context, **arguments) # Pass composite context
                
                try:
                    result_str_for_log = json.dumps(execution_result)
                except TypeError:
                    result_str_for_log = str(execution_result)

                logger.info(f"Tool '{tool_name}' (ID: {invocation_id}) executed by agent '{agent_id}'. Result: {result_str_for_log[:200]}...")
                result_event = ToolResultEvent(tool_name=tool_name, result=execution_result, error=None, tool_invocation_id=invocation_id)
                
                history_content = str(execution_result)
                context.add_message_to_history({ # Convenience method
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": history_content,
                })
                log_msg_result = f"[TOOL_RESULT_DIRECT] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Outcome (first 200 chars): {result_str_for_log[:200]}"
                await tool_log_queue.put(log_msg_result)

            except Exception as e:
                error_message = f"Error executing tool '{tool_name}' (ID: {invocation_id}): {str(e)}"
                logger.error(f"Agent '{agent_id}' {error_message}", exc_info=True)
                result_event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=invocation_id)
                context.add_message_to_history({ # Convenience method
                    "role": "tool",
                    "tool_call_id": invocation_id,
                    "name": tool_name,
                    "content": f"Error: Tool '{tool_name}' execution failed. Reason: {error_message}",
                })
                log_msg_exception = f"[TOOL_EXCEPTION_DIRECT] Agent_ID: {agent_id}, Tool: {tool_name}, Invocation_ID: {invocation_id}, Exception: {error_message}"
                await tool_log_queue.put(log_msg_exception)
        
        await context.queues.enqueue_tool_result(result_event) # Convenience property
        logger.debug(f"Agent '{agent_id}' enqueued ToolResultEvent (direct exec) for '{tool_name}' (ID: {invocation_id}).")


    async def handle(self,
                     event: PendingToolInvocationEvent, 
                     context: 'AgentContext') -> None: 
        if not isinstance(event, PendingToolInvocationEvent): 
            logger.warning(f"ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent: {type(event)}. Skipping.")
            return

        tool_invocation: ToolInvocation = event.tool_invocation
        agent_id = context.agent_id 
        
        if not context.auto_execute_tools:
            logger.info(f"Agent '{agent_id}': Tool '{tool_invocation.name}' (ID: {tool_invocation.id}) requires approval. Storing pending invocation.")
            
            context.store_pending_tool_invocation(tool_invocation) 

            # External event emission logic has been REMOVED from here.
            # An external system or observer would now be responsible for detecting this state
            # (e.g., by monitoring pending_tool_approvals or specific internal agent events if designed for it)
            # and triggering external notifications if required.

            try:
                arguments_json_str = json.dumps(tool_invocation.arguments or {})
            except TypeError:
                logger.warning(f"Could not serialize args for history tool_call for '{tool_invocation.name}'.")
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
            logger.debug(f"Agent '{agent_id}': Added assistant tool_calls to history for pending approval of '{tool_invocation.name}' (ID: {tool_invocation.id}). "
                         "External event emission for approval request is no longer handled here.")
        else: 
            logger.info(f"Agent '{agent_id}': Tool '{tool_invocation.name}' (ID: {tool_invocation.id}) exec auto (auto_execute_tools=True).")
            await self._execute_tool_directly(tool_invocation, context)

