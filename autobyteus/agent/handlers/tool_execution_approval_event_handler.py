# file: autobyteus/autobyteus/agent/handlers/tool_execution_approval_event_handler.py
import logging
import json 
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import ToolExecutionApprovalEvent, ApprovedToolInvocationEvent, LLMUserMessageReadyEvent 
from autobyteus.llm.user_message import LLMUserMessage

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ToolExecutionApprovalEventHandler(AgentEventHandler):
    """
    Handles ToolExecutionApprovalEvents.
    Retrieves the pending tool invocation from context's state.
    If approved, it enqueues an ApprovedToolInvocationEvent for execution.
    If denied, it updates history and enqueues an LLMUserMessageReadyEvent to inform the LLM.
    """
    def __init__(self):
        logger.info("ToolExecutionApprovalEventHandler initialized.")

    async def handle(self,
                     event: ToolExecutionApprovalEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, ToolExecutionApprovalEvent):
            logger.warning(f"ToolExecutionApprovalEventHandler received non-ToolExecutionApprovalEvent: {type(event)}. Skipping.")
            return

        logger.info(
            f"Agent '{context.agent_id}' handling ToolExecutionApprovalEvent for "
            f"tool_invocation_id '{event.tool_invocation_id}': "
            f"Approved={event.is_approved}, Reason='{event.reason if event.reason else 'N/A'}'."
        )

        retrieved_invocation = context.state.retrieve_pending_tool_invocation(event.tool_invocation_id)

        if not retrieved_invocation:
            logger.warning(
                f"Agent '{context.agent_id}': No pending tool invocation found for ID '{event.tool_invocation_id}'. "
                f"Cannot proceed with approval/denial."
            )
            return

        if event.is_approved:
            logger.info(
                f"Agent '{context.agent_id}': Tool invocation '{retrieved_invocation.name}' "
                f"(ID: {event.tool_invocation_id}) was APPROVED. Reason: '{event.reason or 'None'}'. "
                f"Enqueuing ApprovedToolInvocationEvent for execution."
            )            
            approved_event = ApprovedToolInvocationEvent(tool_invocation=retrieved_invocation)
            await context.input_event_queues.enqueue_internal_system_event(approved_event)
            logger.debug(f"Agent '{context.agent_id}': Enqueued ApprovedToolInvocationEvent for '{retrieved_invocation.name}' (ID: {event.tool_invocation_id}).")

        else: 
            logger.warning(
                f"Agent '{context.agent_id}': Tool invocation '{retrieved_invocation.name}' "
                f"(ID: {event.tool_invocation_id}) was DENIED. Reason: '{event.reason or 'None'}'. "
                f"Informing LLM."
            )

            denial_reason_str = event.reason or "No specific reason provided."
            denial_content_for_history = f"Tool execution denied by user/system. Reason: {denial_reason_str}"
            
            context.state.add_message_to_history({
                "role": "tool",
                "tool_call_id": event.tool_invocation_id, 
                "name": retrieved_invocation.name,
                "content": denial_content_for_history,
            })
            logger.debug(f"Agent '{context.agent_id}': Added 'tool' role denial message to history for '{retrieved_invocation.name}' (ID: {event.tool_invocation_id}).")
            
            prompt_content_for_llm = (
                f"The request to use the tool '{retrieved_invocation.name}' "
                f"(with arguments: {json.dumps(retrieved_invocation.arguments or {})}) was denied. "
                f"Denial reason: '{denial_reason_str}'. "
                "Please analyze this outcome and the conversation history, then decide on the next course of action."
            )
            llm_user_message = LLMUserMessage(content=prompt_content_for_llm)
            
            llm_user_message_ready_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message) 
            await context.input_event_queues.enqueue_internal_system_event(llm_user_message_ready_event)
            logger.debug(f"Agent '{context.agent_id}': Enqueued LLMUserMessageReadyEvent to inform LLM of tool denial for '{retrieved_invocation.name}' (ID: {event.tool_invocation_id}).")
