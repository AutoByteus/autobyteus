# file: autobyteus/autobyteus/agent/handlers/tool_result_event_handler.py
import logging
import json 
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler 
from autobyteus.agent.events import ToolResultEvent, LLMUserMessageReadyEvent 
from autobyteus.llm.user_message import LLMUserMessage 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class ToolResultEventHandler(AgentEventHandler):
    """
    Handles ToolResultEvents by formatting the tool's output (or error)
    as a new LLMUserMessage, logging this outcome to `tool_interaction_log_queue`,
    and enqueuing an LLMUserMessageReadyEvent for further LLM processing.
    """
    def __init__(self):
        logger.info("ToolResultEventHandler initialized.")

    async def handle(self,
                     event: ToolResultEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, ToolResultEvent): 
            logger.warning(f"ToolResultEventHandler received non-ToolResultEvent: {type(event)}. Skipping.")
            return

        tool_invocation_id = event.tool_invocation_id if event.tool_invocation_id else 'N/A'

        logger.info(f"Agent '{context.agent_id}' handling ToolResultEvent from tool: '{event.tool_name}' (Invocation ID: {tool_invocation_id}). Error: {event.error is not None}")
        
        if event.error:
            logger.debug(f"Agent '{context.agent_id}' tool '{event.tool_name}' (ID: {tool_invocation_id}) raw error details: {event.error}")
        else:
            try:
                raw_result_str_for_debug_log = json.dumps(event.result, indent=2)
            except TypeError: 
                raw_result_str_for_debug_log = str(event.result)
            logger.debug(f"Agent '{context.agent_id}' tool '{event.tool_name}' (ID: {tool_invocation_id}) raw result:\n---\n{raw_result_str_for_debug_log}\n---")


        content_for_llm: str
        if event.error:
            content_for_llm = (
                f"The tool '{event.tool_name}' (invocation ID: {tool_invocation_id}) encountered an error.\n"
                f"Error details: {event.error}\n"
                f"Please analyze this error and decide the next course of action."
            )
            log_msg_error_processed = f"[TOOL_RESULT_ERROR_PROCESSED] Agent_ID: {context.agent_id}, Tool: {event.tool_name}, Invocation_ID: {tool_invocation_id}, Error: {event.error}"
            await context.output_data_queues.enqueue_tool_interaction_log(log_msg_error_processed)
        else:
            try:
                result_str_for_llm = json.dumps(event.result, indent=2) if not isinstance(event.result, str) else event.result
            except TypeError:
                result_str_for_llm = str(event.result)

            max_len = 2000  
            if len(result_str_for_llm) > max_len:
                original_len = len(str(event.result)) 
                result_str_for_llm = result_str_for_llm[:max_len] + f"... (result truncated, original length {original_len})"
            
            content_for_llm = (
                f"The tool '{event.tool_name}' (invocation ID: {tool_invocation_id}) has executed.\n"
                f"Result:\n{result_str_for_llm}\n" 
                f"Based on this result, what is the next step or final answer?"
            )
            log_msg_success_processed = f"[TOOL_RESULT_SUCCESS_PROCESSED] Agent_ID: {context.agent_id}, Tool: {event.tool_name}, Invocation_ID: {tool_invocation_id}, Result (first 200 chars of stringified): {str(event.result)[:200]}"
            await context.output_data_queues.enqueue_tool_interaction_log(log_msg_success_processed)
        
        logger.debug(f"Agent '{context.agent_id}' preparing message for LLM based on tool '{event.tool_name}' (ID: {tool_invocation_id}) result:\n---\n{content_for_llm}\n---")
        llm_user_message = LLMUserMessage(content=content_for_llm)
        
        next_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message) 
        await context.input_event_queues.enqueue_internal_system_event(next_event)
        
        logger.info(f"Agent '{context.agent_id}' enqueued LLMUserMessageReadyEvent for LLM based on tool '{event.tool_name}' (ID: {tool_invocation_id}) result summary.") 
