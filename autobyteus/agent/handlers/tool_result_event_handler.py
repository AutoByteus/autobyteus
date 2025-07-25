# file: autobyteus/autobyteus/agent/handlers/tool_result_event_handler.py
import logging
import json 
from typing import TYPE_CHECKING, Optional 

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler 
from autobyteus.agent.events import ToolResultEvent, LLMUserMessageReadyEvent 
from autobyteus.llm.user_message import LLMUserMessage 
from autobyteus.agent.tool_execution_result_processor import BaseToolExecutionResultProcessor

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 

logger = logging.getLogger(__name__)

class ToolResultEventHandler(AgentEventHandler):
    """
    Handles ToolResultEvents by formatting the tool's output (or error)
    as a new LLMUserMessage, emitting AGENT_DATA_TOOL_LOG event for this outcome,
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

        agent_id = context.agent_id
        processed_event = event

        # --- New: Apply Tool Execution Result Processors ---
        processor_instances = context.config.tool_execution_result_processors
        if processor_instances:
            processor_names = [p.get_name() for p in processor_instances]
            logger.debug(f"Agent '{agent_id}': Applying tool execution result processors: {processor_names}")
            for processor_instance in processor_instances:
                processor_name_for_log = "unknown"
                try:
                    if not isinstance(processor_instance, BaseToolExecutionResultProcessor):
                        logger.error(f"Agent '{agent_id}': Invalid tool result processor type: {type(processor_instance)}. Skipping.")
                        continue
                    
                    processor_name_for_log = processor_instance.get_name()
                    logger.debug(f"Agent '{agent_id}': Applying tool result processor '{processor_name_for_log}'.")
                    
                    event_before_proc = processed_event
                    processed_event = await processor_instance.process(event_before_proc, context)
                    logger.info(f"Agent '{agent_id}': Tool result processor '{processor_name_for_log}' applied successfully.")

                except Exception as e:
                    logger.error(f"Agent '{agent_id}': Error applying tool result processor '{processor_name_for_log}': {e}. "
                                 f"Skipping and continuing with result from before this processor.", exc_info=True)
                    processed_event = event_before_proc
        # --- End New ---

        tool_invocation_id = processed_event.tool_invocation_id if processed_event.tool_invocation_id else 'N/A'

        logger.info(f"Agent '{agent_id}' handling processed ToolResultEvent from tool: '{processed_event.tool_name}' (Invocation ID: {tool_invocation_id}). Error: {processed_event.error is not None}")
        
        notifier: Optional['AgentExternalEventNotifier'] = None
        if context.phase_manager:
            notifier = context.phase_manager.notifier
        
        if not notifier: # pragma: no cover
            logger.error(f"Agent '{agent_id}': Notifier not available in ToolResultEventHandler. Tool result processing logs will not be emitted.")

        if processed_event.error:
            logger.debug(f"Agent '{agent_id}' tool '{processed_event.tool_name}' (ID: {tool_invocation_id}) raw error details: {processed_event.error}")
        else:
            try:
                raw_result_str_for_debug_log = json.dumps(processed_event.result, indent=2)
            except TypeError: # pragma: no cover
                raw_result_str_for_debug_log = str(processed_event.result)
            logger.debug(f"Agent '{agent_id}' tool '{processed_event.tool_name}' (ID: {tool_invocation_id}) raw result:\n---\n{raw_result_str_for_debug_log}\n---")


        content_for_llm: str
        if processed_event.error:
            content_for_llm = (
                f"The tool '{processed_event.tool_name}' (invocation ID: {tool_invocation_id}) encountered an error.\n"
                f"Error details: {processed_event.error}\n"
                f"Please analyze this error and decide the next course of action."
            )
            log_msg_error_processed = f"[TOOL_RESULT_ERROR_PROCESSED] Agent_ID: {agent_id}, Tool: {processed_event.tool_name}, Invocation_ID: {tool_invocation_id}, Error: {processed_event.error}"
            if notifier:
                try:
                    log_data = {
                        "log_entry": log_msg_error_processed,
                        "tool_invocation_id": tool_invocation_id,
                        "tool_name": processed_event.tool_name,
                    }
                    notifier.notify_agent_data_tool_log(log_data)
                except Exception as e_notify: 
                    logger.error(f"Agent '{agent_id}': Error notifying tool result error log: {e_notify}", exc_info=True)
        else:
            try:
                result_str_for_llm = json.dumps(processed_event.result, indent=2) if not isinstance(processed_event.result, str) else processed_event.result
            except TypeError: # pragma: no cover
                result_str_for_llm = str(processed_event.result)

            content_for_llm = (
                f"The tool '{processed_event.tool_name}' (invocation ID: {tool_invocation_id}) has executed.\n"
                f"Result:\n{result_str_for_llm}\n" 
                f"Based on this result, what is the next step or final answer?"
            )
            log_msg_success_processed = f"[TOOL_RESULT_SUCCESS_PROCESSED] Agent_ID: {agent_id}, Tool: {processed_event.tool_name}, Invocation_ID: {tool_invocation_id}, Result (first 200 chars of stringified): {str(processed_event.result)[:200]}"
            if notifier:
                try:
                    log_data = {
                        "log_entry": log_msg_success_processed,
                        "tool_invocation_id": tool_invocation_id,
                        "tool_name": processed_event.tool_name,
                    }
                    notifier.notify_agent_data_tool_log(log_data)
                except Exception as e_notify: 
                    logger.error(f"Agent '{agent_id}': Error notifying tool result success log: {e_notify}", exc_info=True)
        
        logger.debug(f"Agent '{agent_id}' preparing message for LLM based on tool '{processed_event.tool_name}' (ID: {tool_invocation_id}) result:\n---\n{content_for_llm}\n---")
        llm_user_message = LLMUserMessage(content=content_for_llm)
        
        next_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message) 
        await context.input_event_queues.enqueue_internal_system_event(next_event)
        
        logger.info(f"Agent '{agent_id}' enqueued LLMUserMessageReadyEvent for LLM based on tool '{processed_event.tool_name}' (ID: {tool_invocation_id}) result summary.")
