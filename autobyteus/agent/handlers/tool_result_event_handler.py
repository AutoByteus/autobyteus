# file: autobyteus/autobyteus/agent/handlers/tool_result_event_handler.py
import logging
import json 
from typing import TYPE_CHECKING, Optional, List

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
    Handles ToolResultEvents. It immediately processes and notifies for each
    individual tool result. If a multi-tool call turn is active, it accumulates
    these processed results until the turn is complete, then sends a single
    aggregated message to the LLM.
    """
    def __init__(self):
        logger.info("ToolResultEventHandler initialized.")

    async def _dispatch_aggregated_results_to_llm(self,
                                                  processed_events: List[ToolResultEvent],
                                                  context: 'AgentContext'):
        """
        Aggregates a list of PRE-PROCESSED tool results into a single message and
        dispatches it to the LLM.
        """
        agent_id = context.agent_id
        
        # --- Aggregate results into a single message ---
        aggregated_content_parts = []
        for p_event in processed_events:
            tool_invocation_id = p_event.tool_invocation_id if p_event.tool_invocation_id else 'N/A'
            content_part: str
            if p_event.error:
                content_part = (
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Error\n"
                    f"Details: {p_event.error}"
                )
            else:
                try:
                    result_str = json.dumps(p_event.result, indent=2) if not isinstance(p_event.result, str) else p_event.result
                except TypeError: # pragma: no cover
                    result_str = str(p_event.result)
                content_part = (
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Success\n"
                    f"Result:\n{result_str}" 
                )
            aggregated_content_parts.append(content_part)

        final_content_for_llm = (
            "The following tool executions have completed. Please analyze their results and decide the next course of action.\n\n"
            + "\n\n---\n\n".join(aggregated_content_parts)
        )
        
        logger.debug(f"Agent '{agent_id}' preparing aggregated message for LLM:\n---\n{final_content_for_llm}\n---")
        llm_user_message = LLMUserMessage(content=final_content_for_llm)
        
        next_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message) 
        await context.input_event_queues.enqueue_internal_system_event(next_event)
        
        logger.info(f"Agent '{agent_id}' enqueued LLMUserMessageReadyEvent with aggregated results from {len(processed_events)} tool(s).")


    async def handle(self,
                     event: ToolResultEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, ToolResultEvent): 
            logger.warning(f"ToolResultEventHandler received non-ToolResultEvent: {type(event)}. Skipping.")
            return

        agent_id = context.agent_id
        notifier: Optional['AgentExternalEventNotifier'] = context.phase_manager.notifier if context.phase_manager else None

        # --- Step 1: Immediately process the incoming event ---
        processed_event = event
        processor_instances = context.config.tool_execution_result_processors
        if processor_instances:
            for processor_instance in processor_instances:
                if not isinstance(processor_instance, BaseToolExecutionResultProcessor):
                    logger.error(f"Agent '{agent_id}': Invalid tool result processor type: {type(processor_instance)}. Skipping.")
                    continue
                try:
                    processed_event = await processor_instance.process(processed_event, context)
                except Exception as e:
                    logger.error(f"Agent '{agent_id}': Error applying tool result processor '{processor_instance.get_name()}': {e}", exc_info=True)
        
        # --- Step 2: Immediately notify the result of this single tool call ---
        tool_invocation_id = processed_event.tool_invocation_id if processed_event.tool_invocation_id else 'N/A'
        if notifier:
            log_message = ""
            if processed_event.error:
                log_message = f"[TOOL_RESULT_ERROR_PROCESSED] Agent_ID: {agent_id}, Tool: {processed_event.tool_name}, Invocation_ID: {tool_invocation_id}, Error: {processed_event.error}"
            else:
                log_message = f"[TOOL_RESULT_SUCCESS_PROCESSED] Agent_ID: {agent_id}, Tool: {processed_event.tool_name}, Invocation_ID: {tool_invocation_id}, Result: {str(processed_event.result)}"
            
            try:
                log_data = {
                    "log_entry": log_message,
                    "tool_invocation_id": tool_invocation_id,
                    "tool_name": processed_event.tool_name,
                }
                notifier.notify_agent_data_tool_log(log_data)
                logger.debug(f"Agent '{agent_id}': Notified individual tool result for '{processed_event.tool_name}'.")
            except Exception as e_notify: 
                logger.error(f"Agent '{agent_id}': Error notifying tool result log: {e_notify}", exc_info=True)

        # --- Step 3: Manage the multi-tool call turn state ---
        active_turn = context.state.active_multi_tool_call_turn

        # Case 1: Not a multi-tool call turn, dispatch to LLM immediately.
        if not active_turn:
            logger.info(f"Agent '{agent_id}' handling single ToolResultEvent from tool: '{processed_event.tool_name}'.")
            await self._dispatch_aggregated_results_to_llm([processed_event], context)
            return

        # Case 2: Multi-tool call turn is active, accumulate results.
        active_turn.results.append(processed_event)
        num_results = len(active_turn.results)
        num_expected = len(active_turn.invocations)
        logger.info(f"Agent '{agent_id}' handling ToolResultEvent for multi-tool call turn. "
                    f"Collected {num_results}/{num_expected} results.")

        # If not all results are in, just wait for the next ToolResultEvent.
        if not active_turn.is_complete():
            return
            
        # If all results are in, dispatch them to the LLM and clean up the turn state.
        logger.info(f"Agent '{agent_id}': All tool results for the turn collected. Aggregating for LLM.")
        await self._dispatch_aggregated_results_to_llm(active_turn.results, context)
        
        context.state.active_multi_tool_call_turn = None
        logger.info(f"Agent '{agent_id}': Multi-tool call turn state has been cleared.")
