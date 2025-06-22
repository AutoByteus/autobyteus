import asyncio
import logging
import sys
from typing import Optional, List, Dict, Any
import json 

from autobyteus.agent.agent import Agent
from autobyteus.agent.context.phases import AgentOperationalPhase
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
from autobyteus.agent.streaming.stream_event_payloads import (
    AssistantChunkData,
    AssistantCompleteResponseData,
    ToolInvocationApprovalRequestedData,
    ToolInteractionLogEntryData,
    AgentOperationalPhaseTransitionData,
    ErrorEventData,
)

logger = logging.getLogger(__name__) 

class InteractiveCLIManager:
    """
    Manages the state and rendering logic for the interactive CLI session.
    Input reading is handled by the main `run` loop. This class only handles output.
    """
    def __init__(self, agent_turn_complete_event: asyncio.Event, show_tool_logs: bool, show_token_usage: bool):
        self.agent_turn_complete_event = agent_turn_complete_event
        self.show_tool_logs = show_tool_logs
        self.show_token_usage = show_token_usage
        self.current_line_empty = True
        self.agent_has_spoken_this_turn = False
        self.pending_approval_data: Optional[ToolInvocationApprovalRequestedData] = None
        self.is_thinking = False
        self.is_in_content_block = False

    def reset_turn_state(self):
        """Resets flags that are tracked on a per-turn basis."""
        self._end_thinking_block()
        self.agent_has_spoken_this_turn = False
        self.is_in_content_block = False

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

    def _display_tool_approval_prompt(self):
        """Displays the tool approval prompt using stored pending data."""
        if not self.pending_approval_data:
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

    async def handle_stream_event(self, event: StreamEvent):
        """Processes a single StreamEvent and updates the CLI display."""
        # A block of thinking ends if any event other than a reasoning chunk arrives.
        is_reasoning_only_chunk = (
            event.event_type == StreamEventType.ASSISTANT_CHUNK and
            isinstance(event.data, AssistantChunkData) and
            bool(event.data.reasoning) and not bool(event.data.content)
        )
        if not is_reasoning_only_chunk:
            self._end_thinking_block()

        # Most events should start on a new line.
        if event.event_type != StreamEventType.ASSISTANT_CHUNK:
            self._ensure_new_line()

        if event.event_type in [
            StreamEventType.AGENT_IDLE,
            StreamEventType.ERROR_EVENT,
            StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED,
        ]:
            self.agent_turn_complete_event.set()

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
                    self.current_line_empty = True # We just printed a newline
                
                sys.stdout.write(event.data.reasoning)
                sys.stdout.flush()
                self.current_line_empty = event.data.reasoning.endswith('\n')

            # Stream content to stdout.
            if event.data.content:
                if not self.is_in_content_block:
                    self._ensure_new_line() # Ensures content starts on a new line after </Thinking>
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

        elif event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE and isinstance(event.data, AssistantCompleteResponseData):
            # The reasoning has already been streamed. Do not log it again.
            
            if not self.agent_has_spoken_this_turn:
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
            self._display_tool_approval_prompt()

        elif event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY and isinstance(event.data, ToolInteractionLogEntryData):
            if self.show_tool_logs:
                logger.info(f"[Tool Log: {event.data.log_entry}]")

        elif event.event_type == StreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION and isinstance(event.data, AgentOperationalPhaseTransitionData):
            if event.data.new_phase == AgentOperationalPhase.EXECUTING_TOOL:
                tool_name = event.data.tool_name or "a tool"
                sys.stdout.write(f"Agent: Waiting for tool '{tool_name}' to complete...\n")
                sys.stdout.flush()
                self.current_line_empty = True
                self.agent_has_spoken_this_turn = True
            elif event.data.new_phase == AgentOperationalPhase.BOOTSTRAPPING:
                logger.info("[Agent is initializing...]")
            else:
                phase_msg = f"[Agent Status: {event.data.new_phase.value}"
                if event.data.tool_name:
                    phase_msg += f" ({event.data.tool_name})"
                phase_msg += "]"
                logger.info(phase_msg)

        elif event.event_type == StreamEventType.ERROR_EVENT and isinstance(event.data, ErrorEventData):
            logger.error(f"[Error: {event.data.message} (Source: {event.data.source})]")

        elif event.event_type == StreamEventType.AGENT_IDLE:
            logger.info("[Agent is now idle.]")
        
        else:
            # Add logging for unhandled events for better debugging
            logger.debug(f"CLI Manager: Unhandled StreamEvent type: {event.event_type.value}")


async def run(agent: Agent, show_tool_logs: bool = True, show_token_usage: bool = False, initial_prompt: Optional[str] = None):
    if not isinstance(agent, Agent):
        raise TypeError(f"Expected an Agent instance, got {type(agent).__name__}")

    logger.info(f"Starting interactive CLI session for agent '{agent.agent_id}'.")
    agent_turn_complete_event = asyncio.Event()
    cli_manager = InteractiveCLIManager(agent_turn_complete_event, show_tool_logs, show_token_usage)
    streamer = AgentEventStream(agent)

    async def process_agent_events():
        try:
            async for event in streamer.all_events():
                await cli_manager.handle_stream_event(event)
        except asyncio.CancelledError:
            logger.info("CLI event processing task cancelled.")
        except Exception as e:
            logger.error(f"Error in CLI event processing loop: {e}", exc_info=True)
        finally:
            logger.debug("CLI event processing task finished.")
            agent_turn_complete_event.set() # Ensure main loop isn't stuck

    event_task = asyncio.create_task(process_agent_events())

    try:
        if not agent.is_running:
            agent.start()
        
        logger.debug("Waiting for agent to initialize and become idle...")
        try:
            await asyncio.wait_for(agent_turn_complete_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error(f"Agent did not become idle within 30 seconds. Exiting.")
            # Gracefully exit if agent fails to start
            return

        if initial_prompt:
            logger.info(f"Initial prompt provided: '{initial_prompt}'")
            print(f"You: {initial_prompt}") # Mirroring user input is fine with print
            agent_turn_complete_event.clear()
            cli_manager.reset_turn_state()
            await agent.post_user_message(AgentInputUserMessage(content=initial_prompt))
            await agent_turn_complete_event.wait()
        
        while True:
            agent_turn_complete_event.clear()

            if cli_manager.pending_approval_data:
                logger.debug("Waiting for tool approval from user...")
                approval_input = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                approval_input = approval_input.strip().lower()
                
                approval_data = cli_manager.pending_approval_data
                cli_manager.pending_approval_data = None
                
                is_approved = approval_input in ["y", "yes"]
                reason = "User approved via CLI" if is_approved else "User denied via CLI"

                if is_approved:
                    logger.info(f"User approved tool invocation '{approval_data.invocation_id}'.")
                else:
                    logger.info(f"User denied tool invocation '{approval_data.invocation_id}'.")
                
                await agent.post_tool_execution_approval(approval_data.invocation_id, is_approved, reason)

            else:
                sys.stdout.write("You: ")
                sys.stdout.flush()
                user_input = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                user_input = user_input.rstrip('\n')

                if user_input.lower().strip() in ["/quit", "/exit"]:
                    logger.info("Exit command received.")
                    break
                if not user_input.strip():
                    continue

                logger.debug(f"User input received, posting to agent: '{user_input}'")
                cli_manager.reset_turn_state()
                await agent.post_user_message(AgentInputUserMessage(content=user_input))

            await agent_turn_complete_event.wait()
            logger.debug("Agent turn complete, looping.")

    except (KeyboardInterrupt, EOFError):
        logger.info("Exit signal received. Shutting down CLI.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the CLI main loop: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up and shutting down interactive session...")
        if not event_task.done():
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass # This is expected
        
        if agent.is_running:
            logger.info("Stopping agent...")
            await agent.stop()
        
        logger.info("Closing event stream...")
        await streamer.close()
        logger.info("Interactive session finished.")
