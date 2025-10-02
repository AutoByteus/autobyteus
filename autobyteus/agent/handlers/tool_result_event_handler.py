# file: autobyteus/autobyteus/agent/handlers/tool_result_event_handler.py
import logging
import json 
from typing import TYPE_CHECKING, Optional, List

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler 
from autobyteus.agent.events import ToolResultEvent, UserMessageReceivedEvent
from autobyteus.agent.tool_execution_result_processor import BaseToolExecutionResultProcessor
from autobyteus.agent.message.context_file import ContextFile
from autobyteus.agent.message import AgentInputUserMessage
from autobyteus.agent.sender_type import SenderType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 

logger = logging.getLogger(__name__)

class ToolResultEventHandler(AgentEventHandler):
    """
    Handles ToolResultEvents. It processes and notifies for each individual tool
    result as it arrives. If a multi-tool call turn is active, it accumulates
    these results until the turn is complete, re-orders them to match the original
    invocation sequence, and then sends a single aggregated message to the LLM
    by enqueuing a UserMessageReceivedEvent.
    
    This handler is now "media-aware": if a tool's result is a `ContextFile`
    object, it will be added as multimodal context to the next LLM call rather
    than as plain text.
    """
    def __init__(self):
        logger.info("ToolResultEventHandler initialized.")

    async def _dispatch_results_to_input_pipeline(self,
                                                  processed_events: List[ToolResultEvent],
                                                  context: 'AgentContext'):
        """
        Aggregates a list of PRE-PROCESSED and ORDERED tool results into a single
        AgentInputUserMessage and dispatches it into the main input processing pipeline
        by enqueuing a UserMessageReceivedEvent.
        """
        agent_id = context.agent_id
        
        # --- NEW: Separate text results from media context results ---
        aggregated_content_parts: List[str] = []
        media_context_files: List[ContextFile] = []

        for p_event in processed_events:
            tool_invocation_id = p_event.tool_invocation_id if p_event.tool_invocation_id else 'N/A'
            
            # Check if the result is a ContextFile or a list of them
            result_is_media = False
            if isinstance(p_event.result, ContextFile):
                media_context_files.append(p_event.result)
                aggregated_content_parts.append(
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Success\n"
                    f"Result: The file '{p_event.result.file_name}' has been loaded into the context for you to view."
                )
                result_is_media = True
            elif isinstance(p_event.result, list) and all(isinstance(item, ContextFile) for item in p_event.result):
                media_context_files.extend(p_event.result)
                file_names = [cf.file_name for cf in p_event.result if cf.file_name]
                aggregated_content_parts.append(
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Success\n"
                    f"Result: The following files have been loaded into the context for you to view: {file_names}"
                )
                result_is_media = True

            if result_is_media:
                continue

            # Handle errors
            if p_event.error:
                content_part = (
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Error\n"
                    f"Details: {p_event.error}"
                )
                aggregated_content_parts.append(content_part)
            # Handle standard text/JSON results
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
        
        logger.debug(f"Agent '{agent_id}' preparing aggregated message from tool results for input pipeline:\n---\n{final_content_for_llm}\n---")
        
        # --- REFACTORED: Create an AgentInputUserMessage and route it through the standard input pipeline ---
        agent_input_user_message = AgentInputUserMessage(
            content=final_content_for_llm,
            sender_type=SenderType.TOOL,
            context_files=media_context_files
        )
        
        next_event = UserMessageReceivedEvent(agent_input_user_message=agent_input_user_message)
        await context.input_event_queues.enqueue_user_message(next_event)
        
        logger.info(f"Agent '{agent_id}' enqueued UserMessageReceivedEvent with aggregated results from {len(processed_events)} tool(s) and {len(media_context_files)} media file(s).")


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
            # Sort processors by their order attribute
            sorted_processors = sorted(processor_instances, key=lambda p: p.get_order())
            for processor_instance in sorted_processors:
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
            await self._dispatch_results_to_input_pipeline([processed_event], context)
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
            
        # If all results are in, re-order them and then dispatch to the LLM.
        logger.info(f"Agent '{agent_id}': All tool results for the turn collected. Re-ordering to match invocation sequence.")
        
        # --- NEW RE-ORDERING LOGIC ---
        results_by_id = {res.tool_invocation_id: res for res in active_turn.results}
        sorted_results: List[ToolResultEvent] = []
        for original_invocation in active_turn.invocations:
            result = results_by_id.get(original_invocation.id)
            if result:
                sorted_results.append(result)
            else:
                # This should not happen if the logic is correct, but it's a good safeguard.
                logger.error(f"Agent '{agent_id}': Missing result for invocation ID '{original_invocation.id}' during re-ordering.")
                # Add a synthetic error result to maintain sequence length.
                sorted_results.append(ToolResultEvent(
                    tool_name=original_invocation.name,
                    result=None,
                    error=f"Critical Error: Result for this tool call was lost.",
                    tool_invocation_id=original_invocation.id
                ))

        await self._dispatch_results_to_input_pipeline(sorted_results, context)
        
        context.state.active_multi_tool_call_turn = None
        logger.info(f"Agent '{agent_id}': Multi-tool call turn state has been cleared.")
