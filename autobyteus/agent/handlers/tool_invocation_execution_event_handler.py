import logging
import traceback
from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import ExecuteToolInvocationEvent, ToolResultEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.handlers.tool_lifecycle_payload import (
    build_tool_lifecycle_payload_from_invocation,
)
from autobyteus.utils.llm_output_formatter import format_to_clean_string

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier

logger = logging.getLogger(__name__)


@runtime_checkable
class ToolInvocationPreprocessorLike(Protocol):
    def get_name(self) -> str:
        ...

    def get_order(self) -> int:
        ...

    async def process(self, tool_invocation: ToolInvocation, context: "AgentContext") -> ToolInvocation:
        ...


class ToolInvocationExecutionEventHandler(AgentEventHandler):
    """Handles ExecuteToolInvocationEvent by executing a tool invocation."""

    def __init__(self):
        logger.info("ToolInvocationExecutionEventHandler initialized.")

    async def handle(self, event: ExecuteToolInvocationEvent, context: "AgentContext") -> None:
        if not isinstance(event, ExecuteToolInvocationEvent):
            logger.warning(
                "ToolInvocationExecutionEventHandler received non-ExecuteToolInvocationEvent: %s. Skipping.",
                type(event),
            )
            return

        tool_invocation: ToolInvocation = event.tool_invocation
        tool_name = tool_invocation.name
        arguments = tool_invocation.arguments
        invocation_id = tool_invocation.id
        agent_id = context.agent_id

        notifier: Optional["AgentExternalEventNotifier"] = None
        if context.status_manager:
            notifier = context.status_manager.notifier

        processors = context.config.tool_invocation_preprocessors
        if processors:
            valid_processors = [p for p in processors if isinstance(p, ToolInvocationPreprocessorLike)]
            sorted_processors = sorted(valid_processors, key=lambda p: p.get_order())
            for processor in sorted_processors:
                try:
                    tool_invocation = await processor.process(tool_invocation, context)
                    tool_name = tool_invocation.name
                    arguments = tool_invocation.arguments
                    invocation_id = tool_invocation.id
                except Exception as exc:
                    error_message = (
                        f"Error in tool invocation preprocessor '{processor.get_name()}' for tool "
                        f"'{tool_name}': {exc}"
                    )
                    logger.error("Agent '%s': %s", agent_id, error_message, exc_info=True)
                    result_event = ToolResultEvent(
                        tool_name=tool_name,
                        result=None,
                        error=error_message,
                        tool_invocation_id=invocation_id,
                        turn_id=tool_invocation.turn_id,
                    )
                    await context.input_event_queues.enqueue_tool_result(result_event)
                    return

        if notifier:
            try:
                notifier.notify_agent_tool_execution_started(
                    {
                        **build_tool_lifecycle_payload_from_invocation(agent_id, tool_invocation),
                        "arguments": arguments,
                    }
                )
            except Exception as notify_error:  # pragma: no cover
                logger.error(
                    "Agent '%s': Error notifying tool execution started: %s",
                    agent_id,
                    notify_error,
                    exc_info=True,
                )

        try:
            args_str = format_to_clean_string(arguments)
        except TypeError:
            args_str = str(arguments)

        if notifier:
            try:
                notifier.notify_agent_data_tool_log(
                    {
                        "log_entry": (
                            f"[TOOL_CALL] Agent_ID: {agent_id}, Tool: {tool_name}, "
                            f"Invocation_ID: {invocation_id}, Arguments: {args_str}"
                        ),
                        "tool_invocation_id": invocation_id,
                        "tool_name": tool_name,
                    }
                )
            except Exception as notify_error:  # pragma: no cover
                logger.error(
                    "Agent '%s': Error notifying tool call log: %s",
                    agent_id,
                    notify_error,
                    exc_info=True,
                )

        tool_instance = context.get_tool(tool_name)
        result_event: ToolResultEvent

        if not tool_instance:
            error_message = f"Tool '{tool_name}' not found or configured for agent '{agent_id}'."
            logger.error(error_message)
            result_event = ToolResultEvent(
                tool_name=tool_name,
                result=None,
                error=error_message,
                tool_invocation_id=invocation_id,
                turn_id=tool_invocation.turn_id,
            )
            if notifier:
                try:
                    notifier.notify_agent_data_tool_log(
                        {
                            "log_entry": f"[TOOL_ERROR] {error_message}",
                            "tool_invocation_id": invocation_id,
                            "tool_name": tool_name,
                        }
                    )
                    notifier.notify_agent_error_output_generation(
                        error_source=f"ToolExecution.ToolNotFound.{tool_name}",
                        error_message=error_message,
                    )
                except Exception as notify_error:  # pragma: no cover
                    logger.error(
                        "Agent '%s': Error notifying tool error log/output error: %s",
                        agent_id,
                        notify_error,
                        exc_info=True,
                    )
        else:
            try:
                execution_result = await tool_instance.execute(context=context, **arguments)

                try:
                    result_json_for_log = format_to_clean_string(execution_result)
                except (TypeError, ValueError):
                    result_json_for_log = format_to_clean_string(str(execution_result))

                result_event = ToolResultEvent(
                    tool_name=tool_name,
                    result=execution_result,
                    error=None,
                    tool_invocation_id=invocation_id,
                    tool_args=arguments,
                    turn_id=tool_invocation.turn_id,
                )

                if notifier:
                    try:
                        notifier.notify_agent_data_tool_log(
                            {
                                "log_entry": f"[TOOL_RESULT] {result_json_for_log}",
                                "tool_invocation_id": invocation_id,
                                "tool_name": tool_name,
                            }
                        )
                    except Exception as notify_error:  # pragma: no cover
                        logger.error(
                            "Agent '%s': Error notifying tool result log: %s",
                            agent_id,
                            notify_error,
                            exc_info=True,
                        )
            except Exception as exc:
                error_message = f"Error executing tool '{tool_name}' (ID: {invocation_id}): {exc}"
                error_details = traceback.format_exc()
                logger.error("Agent '%s' %s", agent_id, error_message, exc_info=True)
                result_event = ToolResultEvent(
                    tool_name=tool_name,
                    result=None,
                    error=error_message,
                    tool_invocation_id=invocation_id,
                    turn_id=tool_invocation.turn_id,
                )

                if notifier:
                    try:
                        notifier.notify_agent_data_tool_log(
                            {
                                "log_entry": f"[TOOL_EXCEPTION] {error_message}\nDetails:\n{error_details}",
                                "tool_invocation_id": invocation_id,
                                "tool_name": tool_name,
                            }
                        )
                        notifier.notify_agent_error_output_generation(
                            error_source=f"ToolExecution.Exception.{tool_name}",
                            error_message=error_message,
                            error_details=error_details,
                        )
                    except Exception as notify_error:  # pragma: no cover
                        logger.error(
                            "Agent '%s': Error notifying tool exception log/output error: %s",
                            agent_id,
                            notify_error,
                            exc_info=True,
                        )

        await context.input_event_queues.enqueue_tool_result(result_event)
