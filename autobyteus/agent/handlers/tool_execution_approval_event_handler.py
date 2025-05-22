# file: autobyteus/autobyteus/agent/handlers/tool_execution_approval_event_handler.py
import logging
import json # For formatting messages to LLM
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import ToolExecutionApprovalEvent, ApprovedToolInvocationEvent, LLMPromptReadyEvent
from autobyteus.llm.user_message import LLMUserMessage

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ToolExecutionApprovalEventHandler(AgentEventHandler):
    """
    Handles ToolExecutionApprovalEvents.
    Retrieves the pending tool invocation from context.
    If approved, it enqueues an ApprovedToolInvocationEvent for execution.
    If denied, it updates history and enqueues an LLMPromptReadyEvent to inform the LLM.
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

        retrieved_invocation = context.retrieve_pending_tool_invocation(event.tool_invocation_id)

        if not retrieved_invocation:
            logger.warning(
                f"Agent '{context.agent_id}': No pending tool invocation found for ID '{event.tool_invocation_id}'. "
                f"Cannot proceed with approval/denial. This might happen if the approval event is duplicated or stale."
            )
            # Optionally, inform LLM about this anomaly if it's critical
            # For now, just log and return.
            return

        if event.is_approved:
            logger.info(
                f"Agent '{context.agent_id}': Tool invocation '{retrieved_invocation.name}' "
                f"(ID: {event.tool_invocation_id}) was APPROVED. Reason: '{event.reason or 'None'}'. "
                f"Enqueuing ApprovedToolInvocationEvent for execution."
            )            
            approved_event = ApprovedToolInvocationEvent(tool_invocation=retrieved_invocation)
            # Enqueue to internal_system_event_queue, which AgentRuntime processes
            await context.queues.enqueue_internal_system_event(approved_event)
            logger.debug(f"Agent '{context.agent_id}': Enqueued ApprovedToolInvocationEvent for '{retrieved_invocation.name}' (ID: {event.tool_invocation_id}).")

        else: # Tool execution denied
            logger.warning(
                f"Agent '{context.agent_id}': Tool invocation '{retrieved_invocation.name}' "
                f"(ID: {event.tool_invocation_id}) was DENIED. Reason: '{event.reason or 'None'}'. "
                f"Informing LLM."
            )

            denial_reason_str = event.reason or "No specific reason provided."
            denial_content_for_history = f"Tool execution denied by user/system. Reason: {denial_reason_str}"
            
            # Add OpenAI-compliant "tool" role message to history with the denial
            context.add_message_to_history({
                "role": "tool",
                "tool_call_id": event.tool_invocation_id, # Match the ID from assistant's tool_calls
                "name": retrieved_invocation.name,
                "content": denial_content_for_history,
            })
            logger.debug(f"Agent '{context.agent_id}': Added 'tool' role denial message to history for '{retrieved_invocation.name}' (ID: {event.tool_invocation_id}).")

            # Prepare a message to prompt the LLM to re-plan
            # This message will be added to history by LLMPromptReadyEventHandler as 'user' role.
            # The LLM will then use the full history (including prior assistant tool_calls and this tool denial)
            prompt_content_for_llm = (
                f"The request to use the tool '{retrieved_invocation.name}' "
                f"(with arguments: {json.dumps(retrieved_invocation.arguments or {})}) was denied. "
                f"Denial reason: '{denial_reason_str}'. "
                "Please analyze this outcome and the conversation history, then decide on the next course of action."
            )
            llm_user_message = LLMUserMessage(content=prompt_content_for_llm)
            
            llm_prompt_ready_event = LLMPromptReadyEvent(llm_user_message=llm_user_message)
            await context.queues.enqueue_internal_system_event(llm_prompt_ready_event)
            logger.debug(f"Agent '{context.agent_id}': Enqueued LLMPromptReadyEvent to inform LLM of tool denial for '{retrieved_invocation.name}' (ID: {event.tool_invocation_id}).")
