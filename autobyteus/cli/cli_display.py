import asyncio
import logging
import sys
from typing import Optional
import json 

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
from autobyteus.agent.streaming.stream_event_payloads import (
    AssistantChunkData,
    AssistantCompleteResponseData,
    ToolInvocationApprovalRequestedData,
    ToolInteractionLogEntryData,
    AgentStatusUpdateData,
    ErrorEventData,
    ToolInvocationAutoExecutingData,
    SegmentEventData,
)
from autobyteus.agent.streaming.parser.events import SegmentEventType, SegmentType

logger = logging.getLogger(__name__) 

class InteractiveCLIDisplay:
    """
    Manages the state and rendering logic for the interactive CLI session's display.
    Input reading is handled by the main `run` loop. This class only handles output.
    """
    def __init__(self, agent_turn_complete_event: asyncio.Event, show_tool_logs: bool, show_token_usage: bool):
        self.agent_turn_complete_event = agent_turn_complete_event
        self.show_tool_logs = show_tool_logs
        self.show_token_usage = show_token_usage
        self.current_line_empty = True
        self.agent_has_spoken_this_turn = False
        self.pending_approval_data: Optional[ToolInvocationApprovalRequestedData] = None
        self.approval_prompt_shown: bool = False
        self.current_status: Optional[AgentStatus] = None
        self.awaiting_approval: bool = False
        self.is_thinking = False
        self.is_in_content_block = False
        self._segment_types_by_id = {}
        self._saw_segment_event = False

    def reset_turn_state(self):
        """Resets flags that are tracked on a per-turn basis."""
        self._end_thinking_block()
        self.agent_has_spoken_this_turn = False
        self.is_in_content_block = False
        self._segment_types_by_id.clear()
        self._saw_segment_event = False

    def _ensure_new_line(self):
        """Ensures the cursor is on a new line if the current one isn't empty."""
        if not self.current_line_empty:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self.current_line_empty = True

    def _end_thinking_block(self):
        """Closes the <Thinking> block if it was active."""
        if self.is_thinking:
            sys.stdout.write("\n</Thinking>")
            sys.stdout.flush()
            self.is_thinking = False
            self.current_line_empty = False

    def _ensure_agent_prefix(self):
        """Prints the Agent prefix once per turn."""
        if not self.agent_has_spoken_this_turn:
            self._ensure_new_line()
            sys.stdout.write("Agent:\n")
            sys.stdout.flush()
            self.agent_has_spoken_this_turn = True
            self.current_line_empty = True

    def _handle_segment_event(self, segment_event: SegmentEventData):
        """Render segment events emitted by the streaming parser."""
        try:
            event_type = SegmentEventType(segment_event.event_type)
        except ValueError:
            logger.debug(f"CLI Display: Unknown segment event type '{segment_event.event_type}'.")
            return

        self._saw_segment_event = True

        segment_type = None
        if segment_event.segment_type:
            try:
                segment_type = SegmentType(segment_event.segment_type)
            except ValueError:
                logger.debug(f"CLI Display: Unknown segment type '{segment_event.segment_type}'.")

        if segment_type is None and segment_event.segment_id in self._segment_types_by_id:
            segment_type = self._segment_types_by_id.get(segment_event.segment_id)

        metadata = {}
        if isinstance(segment_event.payload, dict):
            metadata = segment_event.payload.get("metadata", {}) or {}

        if event_type == SegmentEventType.START:
            if segment_type is not None:
                self._segment_types_by_id[segment_event.segment_id] = segment_type

            if segment_type != SegmentType.REASONING:
                self._end_thinking_block()

            self._ensure_agent_prefix()

            if segment_type == SegmentType.REASONING:
                if not self.is_thinking:
                    sys.stdout.write("<Thinking>\n")
                    sys.stdout.flush()
                    self.is_thinking = True
                    self.current_line_empty = True
                return

            if segment_type == SegmentType.FILE:
                path = metadata.get("path", "")
                header = f"<file path=\"{path}\">" if path else "<file>"
                sys.stdout.write(f"{header}\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = True
                return

            if segment_type == SegmentType.BASH:
                sys.stdout.write("<bash>\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = True
                return

            if segment_type == SegmentType.TOOL_CALL:
                tool_name = metadata.get("tool_name", "")
                header = f"<tool name=\"{tool_name}\">" if tool_name else "<tool>"
                sys.stdout.write(f"{header}\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = True
                return

            if segment_type == SegmentType.IFRAME:
                sys.stdout.write("<iframe>\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = True
                return

            # Text segment start does not need a visible marker.
            self.is_in_content_block = True
            return

        if event_type == SegmentEventType.CONTENT:
            if segment_type == SegmentType.REASONING:
                if not self.is_thinking:
                    self._ensure_agent_prefix()
                    sys.stdout.write("<Thinking>\n")
                    sys.stdout.flush()
                    self.is_thinking = True
                delta = segment_event.payload.get("delta", "")
                sys.stdout.write(str(delta))
                sys.stdout.flush()
                self.current_line_empty = str(delta).endswith("\n")
                return

            delta = segment_event.payload.get("delta", "")
            if delta:
                self._ensure_agent_prefix()
                sys.stdout.write(str(delta))
                sys.stdout.flush()
                self.current_line_empty = str(delta).endswith("\n")
                self.is_in_content_block = True
            return

        if event_type == SegmentEventType.END:
            if segment_type == SegmentType.REASONING:
                self._end_thinking_block()
                self._segment_types_by_id.pop(segment_event.segment_id, None)
                return

            if segment_type == SegmentType.FILE:
                sys.stdout.write("\n</file>\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = False
                self._segment_types_by_id.pop(segment_event.segment_id, None)
                return

            if segment_type == SegmentType.BASH:
                sys.stdout.write("\n</bash>\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = False
                self._segment_types_by_id.pop(segment_event.segment_id, None)
                return

            if segment_type == SegmentType.TOOL_CALL:
                sys.stdout.write("\n</tool>\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = False
                self._segment_types_by_id.pop(segment_event.segment_id, None)
                return

            if segment_type == SegmentType.IFRAME:
                sys.stdout.write("\n</iframe>\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.is_in_content_block = False
                self._segment_types_by_id.pop(segment_event.segment_id, None)
                return

            if segment_type == SegmentType.TEXT:
                self.is_in_content_block = False
                self._segment_types_by_id.pop(segment_event.segment_id, None)
                return

            self._segment_types_by_id.pop(segment_event.segment_id, None)

    def _display_tool_approval_prompt(self):
        """Displays the tool approval prompt using stored pending data."""
        if not self.pending_approval_data or self.approval_prompt_shown:
            return
            
        try:
            args_str = json.dumps(self.pending_approval_data.arguments, indent=2)
        except TypeError:
            args_str = str(self.pending_approval_data.arguments)

        self._ensure_new_line()
        prompt_message = (
            f"Tool Call: '{self.pending_approval_data.tool_name}' requests permission to run with arguments:\n"
            f"{args_str}\nApprove? (y/n): "
        )
        sys.stdout.write(prompt_message)
        sys.stdout.flush()
        self.current_line_empty = False
        self.approval_prompt_shown = True

    def clear_pending_approval(self):
        self.pending_approval_data = None
        self.approval_prompt_shown = False

    async def handle_stream_event(self, event: StreamEvent):
        """Processes a single StreamEvent and updates the CLI display."""
        if event.event_type == StreamEventType.SEGMENT_EVENT and isinstance(event.data, SegmentEventData):
            self._handle_segment_event(event.data)
            return

        if event.event_type == StreamEventType.ASSISTANT_CHUNK and isinstance(event.data, AssistantChunkData):
            # If this is the first output from the agent this turn, print the "Agent: " prefix.
            if not self.agent_has_spoken_this_turn:
                self._ensure_new_line()
                sys.stdout.write("Agent:\n")
                sys.stdout.flush()
                self.agent_has_spoken_this_turn = True
                self.current_line_empty = True

            # Stream reasoning to stdout without logger formatting.
            if event.data.reasoning:
                if not self.is_thinking:
                    sys.stdout.write("<Thinking>\n")
                    sys.stdout.flush()
                    self.is_thinking = True
                    self.current_line_empty = True
                
                sys.stdout.write(event.data.reasoning)
                sys.stdout.flush()
                self.current_line_empty = event.data.reasoning.endswith('\n')

            # Stream content to stdout.
            if event.data.content:
                if not self.is_in_content_block:
                    self._ensure_new_line()
                    self.is_in_content_block = True
                sys.stdout.write(event.data.content)
                sys.stdout.flush()
                self.current_line_empty = event.data.content.endswith('\n')
            
            if self.show_token_usage and event.data.is_complete and event.data.usage:
                self._ensure_new_line()
                usage = event.data.usage
                logger.info(
                    f"[Token Usage: Prompt={usage.prompt_tokens}, "
                    f"Completion={usage.completion_tokens}, Total={usage.total_tokens}]"
                )
            return

        self._end_thinking_block()
        self._ensure_new_line()

        if event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE and isinstance(event.data, AssistantCompleteResponseData):
            # The reasoning has already been streamed. Do not log it again.
            
            if not self._saw_segment_event and not self.agent_has_spoken_this_turn:
                # This case handles responses that might not have streamed any content chunks (e.g., only a tool call).
                # We still need to ensure the agent's turn is visibly terminated with a newline.
                self._ensure_new_line()
                
                # If there's final content that wasn't in a chunk, print it.
                if event.data.content:
                    sys.stdout.write(f"Agent: {event.data.content}\n")
                    sys.stdout.flush()

            if self.show_token_usage and event.data.usage:
                self._ensure_new_line()
                usage = event.data.usage
                logger.info(
                    f"[Token Usage: Prompt={usage.prompt_tokens}, "
                    f"Completion={usage.completion_tokens}, Total={usage.total_tokens}]"
                )

            self.current_line_empty = True
            self.reset_turn_state() # Reset for next turn

        elif event.event_type == StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED and isinstance(event.data, ToolInvocationApprovalRequestedData):
            self.pending_approval_data = event.data
            if self.awaiting_approval or self.current_status == AgentStatus.AWAITING_TOOL_APPROVAL:
                self._display_tool_approval_prompt()
                self.agent_turn_complete_event.set()

        elif event.event_type == StreamEventType.TOOL_INVOCATION_AUTO_EXECUTING and isinstance(event.data, ToolInvocationAutoExecutingData):
            tool_name = event.data.tool_name
            self._ensure_new_line()
            sys.stdout.write(f"Agent: Automatically executing tool '{tool_name}'...\n")
            sys.stdout.flush()
            self.current_line_empty = True
            self.agent_has_spoken_this_turn = True

        elif event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY and isinstance(event.data, ToolInteractionLogEntryData):
            if self.show_tool_logs:
                logger.info(
                    f"[Tool Log ({event.data.tool_name} | {event.data.tool_invocation_id})]: {event.data.log_entry}"
                )

        elif event.event_type == StreamEventType.AGENT_STATUS_UPDATED and isinstance(event.data, AgentStatusUpdateData):
            self.current_status = event.data.new_status
            if event.data.new_status == AgentStatus.AWAITING_TOOL_APPROVAL:
                self.awaiting_approval = True
                if self.pending_approval_data:
                    self._display_tool_approval_prompt()
                    self.agent_turn_complete_event.set()
            else:
                self.awaiting_approval = False

            if event.data.new_status in {AgentStatus.IDLE, AgentStatus.ERROR}:
                self.agent_turn_complete_event.set()

            if event.data.new_status == AgentStatus.EXECUTING_TOOL:
                tool_name = event.data.tool_name or "a tool"
                sys.stdout.write(f"Agent: Waiting for tool '{tool_name}' to complete...\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.agent_has_spoken_this_turn = True
            elif event.data.new_status == AgentStatus.IDLE:
                logger.info("[Agent is now idle.]")
            elif event.data.new_status == AgentStatus.BOOTSTRAPPING:
                logger.info("[Agent is initializing...]")
            elif event.data.new_status == AgentStatus.TOOL_DENIED:
                tool_name = event.data.tool_name or "a tool"
                logger.info(f"[Tool '{tool_name}' was denied by user. Agent is reconsidering.]")
            else:
                status_msg = f"[Agent Status: {event.data.new_status.value}"
                if event.data.tool_name:
                    status_msg += f" ({event.data.tool_name})"
                status_msg += "]"
                logger.info(status_msg)

        elif event.event_type == StreamEventType.ERROR_EVENT and isinstance(event.data, ErrorEventData):
            logger.error(f"[Error: {event.data.message} (Source: {event.data.source})]")
            self.agent_turn_complete_event.set()
        
        else:
            # Add logging for unhandled events for better debugging
            logger.debug(f"CLI Display: Unhandled StreamEvent type: {event.event_type.value}")
