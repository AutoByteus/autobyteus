import logging

from typing import TYPE_CHECKING, Optional, List

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import ToolResultEvent, UserMessageReceivedEvent
from autobyteus.agent.tool_execution_result_processor import BaseToolExecutionResultProcessor
from autobyteus.agent.message.context_file import ContextFile
from autobyteus.agent.message import AgentInputUserMessage
from autobyteus.agent.sender_type import SenderType
from autobyteus.agent.handlers.tool_lifecycle_payload import (
    build_tool_lifecycle_payload_from_result,
)
from autobyteus.utils.llm_output_formatter import format_to_clean_string

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier

logger = logging.getLogger(__name__)


class ToolResultEventHandler(AgentEventHandler):
    """
    Handles ToolResultEvents and routes aggregated results back into the input pipeline.
    """

    def __init__(self):
        logger.info("ToolResultEventHandler initialized.")

    async def _dispatch_results_to_input_pipeline(
        self,
        processed_events: List[ToolResultEvent],
        context: "AgentContext",
    ):
        agent_id = context.agent_id

        aggregated_content_parts: List[str] = []
        media_context_files: List[ContextFile] = []

        for p_event in processed_events:
            tool_invocation_id = p_event.tool_invocation_id if p_event.tool_invocation_id else "N/A"

            if p_event.is_denied:
                aggregated_content_parts.append(
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Denied\n"
                    f"Details: {p_event.error or 'Tool execution denied.'}"
                )
                continue

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

            if p_event.error:
                aggregated_content_parts.append(
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Error\n"
                    f"Details: {p_event.error}"
                )
            else:
                result_str = format_to_clean_string(p_event.result)
                aggregated_content_parts.append(
                    f"Tool: {p_event.tool_name} (ID: {tool_invocation_id})\n"
                    f"Status: Success\n"
                    f"Result:\n{result_str}"
                )

        final_content_for_llm = (
            "The following tool executions have completed. Please analyze their results and decide the next course of action.\n\n"
            + "\n\n---\n\n".join(aggregated_content_parts)
        )

        logger.debug(
            "Agent '%s' preparing aggregated message from tool results for input pipeline:\n---\n%s\n---",
            agent_id,
            final_content_for_llm,
        )

        agent_input_user_message = AgentInputUserMessage(
            content=final_content_for_llm,
            sender_type=SenderType.TOOL,
            context_files=media_context_files,
        )

        next_event = UserMessageReceivedEvent(agent_input_user_message=agent_input_user_message)
        await context.input_event_queues.enqueue_user_message(next_event)

        logger.info(
            "Agent '%s' enqueued UserMessageReceivedEvent with aggregated results from %d tool(s) and %d media file(s).",
            agent_id,
            len(processed_events),
            len(media_context_files),
        )

    def _emit_terminal_lifecycle(self, processed_event: ToolResultEvent, context: "AgentContext") -> None:
        if processed_event.is_denied:
            return

        notifier = context.status_manager.notifier if context.status_manager else None
        if not notifier:
            return

        payload_base = build_tool_lifecycle_payload_from_result(context.agent_id, processed_event)

        if processed_event.error:
            notifier.notify_agent_tool_execution_failed(
                {
                    **payload_base,
                    "error": processed_event.error,
                }
            )
            return

        notifier.notify_agent_tool_execution_succeeded(
            {
                **payload_base,
                "result": processed_event.result,
            }
        )

    async def handle(self, event: ToolResultEvent, context: "AgentContext") -> None:
        if not isinstance(event, ToolResultEvent):
            logger.warning(
                "ToolResultEventHandler received non-ToolResultEvent: %s. Skipping.",
                type(event),
            )
            return

        if not event.turn_id and context.state.active_turn_id:
            event.turn_id = context.state.active_turn_id

        agent_id = context.agent_id
        notifier: Optional["AgentExternalEventNotifier"] = (
            context.status_manager.notifier if context.status_manager else None
        )

        processed_event = event
        processor_instances = context.config.tool_execution_result_processors
        if processor_instances:
            sorted_processors = sorted(processor_instances, key=lambda p: p.get_order())
            for processor_instance in sorted_processors:
                if not isinstance(processor_instance, BaseToolExecutionResultProcessor):
                    logger.error(
                        "Agent '%s': Invalid tool result processor type: %s. Skipping.",
                        agent_id,
                        type(processor_instance),
                    )
                    continue
                try:
                    processed_event = await processor_instance.process(processed_event, context)
                except Exception as exc:
                    logger.error(
                        "Agent '%s': Error applying tool result processor '%s': %s",
                        agent_id,
                        processor_instance.get_name(),
                        exc,
                        exc_info=True,
                    )

        tool_invocation_id = processed_event.tool_invocation_id if processed_event.tool_invocation_id else "N/A"
        if notifier:
            if processed_event.is_denied:
                log_message = (
                    f"[TOOL_RESULT_DENIED] Agent_ID: {agent_id}, Tool: {processed_event.tool_name}, "
                    f"Invocation_ID: {tool_invocation_id}, Reason: {processed_event.error or 'Denied'}"
                )
            elif processed_event.error:
                log_message = (
                    f"[TOOL_RESULT_ERROR_PROCESSED] Agent_ID: {agent_id}, Tool: {processed_event.tool_name}, "
                    f"Invocation_ID: {tool_invocation_id}, Error: {processed_event.error}"
                )
            else:
                log_message = (
                    f"[TOOL_RESULT_SUCCESS_PROCESSED] Agent_ID: {agent_id}, Tool: {processed_event.tool_name}, "
                    f"Invocation_ID: {tool_invocation_id}, Result: {format_to_clean_string(processed_event.result)}"
                )

            try:
                notifier.notify_agent_data_tool_log(
                    {
                        "log_entry": log_message,
                        "tool_invocation_id": tool_invocation_id,
                        "tool_name": processed_event.tool_name,
                    }
                )
            except Exception as notify_error:  # pragma: no cover
                logger.error(
                    "Agent '%s': Error notifying tool result log: %s",
                    agent_id,
                    notify_error,
                    exc_info=True,
                )

        self._emit_terminal_lifecycle(processed_event, context)

        active_turn = context.state.active_multi_tool_call_turn

        if not active_turn:
            logger.info(
                "Agent '%s' handling single ToolResultEvent from tool: '%s'.",
                agent_id,
                processed_event.tool_name,
            )
            await self._dispatch_results_to_input_pipeline([processed_event], context)
            return

        active_turn.results.append(processed_event)
        num_results = len(active_turn.results)
        num_expected = len(active_turn.invocations)
        logger.info(
            "Agent '%s' handling ToolResultEvent for multi-tool call turn. Collected %d/%d results.",
            agent_id,
            num_results,
            num_expected,
        )

        if not active_turn.is_complete():
            return

        logger.info(
            "Agent '%s': All tool results for the turn collected. Re-ordering to match invocation sequence.",
            agent_id,
        )

        results_by_id = {res.tool_invocation_id: res for res in active_turn.results}
        sorted_results: List[ToolResultEvent] = []
        for original_invocation in active_turn.invocations:
            result = results_by_id.get(original_invocation.id)
            if result:
                sorted_results.append(result)
            else:
                logger.error(
                    "Agent '%s': Missing result for invocation ID '%s' during re-ordering.",
                    agent_id,
                    original_invocation.id,
                )
                sorted_results.append(
                    ToolResultEvent(
                        tool_name=original_invocation.name,
                        result=None,
                        error="Critical Error: Result for this tool call was lost.",
                        tool_invocation_id=original_invocation.id,
                        turn_id=original_invocation.turn_id,
                    )
                )

        await self._dispatch_results_to_input_pipeline(sorted_results, context)

        context.state.active_multi_tool_call_turn = None
        logger.info("Agent '%s': Multi-tool call turn state has been cleared.", agent_id)
