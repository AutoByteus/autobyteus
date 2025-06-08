# file: autobyteus/autobyteus/cli/agent_cli.py
import asyncio
import logging
import sys
from typing import Optional, List, Dict, Any
import json 

from autobyteus.agent.agent import Agent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
# Import specific payload types for isinstance checks and attribute access
from autobyteus.agent.streaming.stream_event_payloads import (
    AssistantChunkData,
    AssistantCompleteResponseData,
    ToolInvocationApprovalRequestedData,
    ToolInteractionLogEntryData,
    AgentOperationalPhaseTransitionData,
    ErrorEventData,
    EmptyData
)
from autobyteus.agent.context.phases import AgentOperationalPhase 

# General logger for the CLI module
logger = logging.getLogger(__name__) 

# Specific logger for interactive, unformatted output to replicate print()
interactive_logger = logging.getLogger("autobyteus.cli.interactive")

class InteractiveCLIManager:
    """
    Manages the state and rendering logic for the interactive CLI session.
    Input reading is handled by the main `run` loop. This class only handles output.
    All output is sent through the logging system.
    """
    def __init__(self, 
                 agent_turn_complete_event: asyncio.Event, 
                 show_tool_logs: bool,
                 cli_session_agent_id: str):
        self.agent_turn_complete_event = agent_turn_complete_event
        self.show_tool_logs = show_tool_logs
        self.cli_session_agent_id = cli_session_agent_id

        self.current_line_empty: bool = True
        self.agent_has_spoken_this_turn: bool = False
        self.pending_approval_invocation_id: Optional[str] = None

    def _ensure_new_line(self):
        """Ensures the cursor is on a new line if the current one isn't empty."""
        if not self.current_line_empty:
            interactive_logger.info("") # Will print a newline
            self.current_line_empty = True

    def _display_tool_approval_prompt(self, tool_approval_payload: ToolInvocationApprovalRequestedData):
        """
        Displays the tool approval prompt and sets the state to wait for input.
        It does NOT read from stdin.
        """
        invocation_id = tool_approval_payload.invocation_id
        tool_name = tool_approval_payload.tool_name
        arguments = tool_approval_payload.arguments
        event_agent_id = self.cli_session_agent_id

        if not all([invocation_id, tool_name is not None]):
            logger.error(f"[{event_agent_id}] Invalid data for tool approval request: {tool_approval_payload}")
            self.agent_turn_complete_event.set() # Unblock the main loop to prevent a hang
            return

        try:
            args_str = json.dumps(arguments, indent=2)
        except TypeError:
            args_str = str(arguments)

        self._ensure_new_line()
        prompt_message = (
            f"Tool Call ({event_agent_id}): '{tool_name}' (Invocation ID: {invocation_id}) requests permission to run with arguments:\n"
            f"{args_str}\nApprove? (y/n): "
        )
        # Use a custom logging adapter or extra dict to control `end`
        # For simplicity, we'll handle this by constructing the log message carefully.
        # The handler should not add a newline for this specific logger.
        # A more robust solution might involve custom handlers, but this is a good start.
        sys.stdout.write(prompt_message)
        sys.stdout.flush()
        self.current_line_empty = False

        # Set state for the main loop to handle input
        self.pending_approval_invocation_id = invocation_id
        # Signal the main loop that input is now required
        self.agent_turn_complete_event.set()


    async def handle_stream_event(self, event: StreamEvent):
        """Processes a single StreamEvent and updates the CLI display."""
        logger.debug(f"CLI handle_stream_event: Received event of type {event.event_type.value}")
        event_origin_agent_id = event.agent_id or self.cli_session_agent_id

        # Always ensure a new line for non-chunk events for better formatting.
        if event.event_type != StreamEventType.ASSISTANT_CHUNK:
            self._ensure_new_line()

        # Reset 'agent has spoken' flag for any event that isn't part of a continuous agent speech stream.
        if event.event_type not in [StreamEventType.ASSISTANT_CHUNK, StreamEventType.ASSISTANT_COMPLETE_RESPONSE]:
             self.agent_has_spoken_this_turn = False

        if event.event_type == StreamEventType.ASSISTANT_CHUNK:
            if isinstance(event.data, AssistantChunkData):
                chunk_content = event.data.content
                if not self.agent_has_spoken_this_turn:
                    # Use stdout directly for streaming to avoid logger overhead/formatting
                    sys.stdout.write(f"Agent ({event_origin_agent_id}): ")
                    sys.stdout.flush()
                    self.agent_has_spoken_this_turn = True
                    self.current_line_empty = False 
                
                sys.stdout.write(chunk_content)
                sys.stdout.flush()
                if '\n' in chunk_content: # More robust check for newlines
                    self.current_line_empty = chunk_content.endswith('\n')
                else:
                    self.current_line_empty = False
            else:
                logger.warning(f"[{self.cli_session_agent_id}] Received ASSISTANT_CHUNK with unexpected data type: {type(event.data)}")

        elif event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE:
            if isinstance(event.data, AssistantCompleteResponseData):
                complete_resp_content = event.data.content
                # If the agent hasn't spoken via chunks, print the whole response.
                if not self.agent_has_spoken_this_turn and complete_resp_content:
                    interactive_logger.info(f"Agent ({event_origin_agent_id}): {complete_resp_content}")
                
                # Ensure we end on a new line after any assistant message.
                self._ensure_new_line()
                logger.debug(f"[{self.cli_session_agent_id}] Received ASSISTANT_COMPLETE_RESPONSE.")
            else:
                 logger.warning(f"[{self.cli_session_agent_id}] Received ASSISTANT_COMPLETE_RESPONSE with unexpected data type: {type(event.data)}")

        elif event.event_type == StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED:
            if isinstance(event.data, ToolInvocationApprovalRequestedData):
                logger.debug(f"[{self.cli_session_agent_id}] Handling TOOL_INVOCATION_APPROVAL_REQUESTED event. Data: {event.data}")
                self._display_tool_approval_prompt(event.data)
            else:
                logger.warning(f"[{self.cli_session_agent_id}] Received TOOL_INVOCATION_APPROVAL_REQUESTED with unexpected data type: {type(event.data)}")

        elif event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            if isinstance(event.data, ToolInteractionLogEntryData):
                if self.show_tool_logs:
                    interactive_logger.info(f"Tool Log ({event_origin_agent_id}): {event.data.log_entry}")
            else:
                logger.warning(f"[{self.cli_session_agent_id}] Received TOOL_INTERACTION_LOG_ENTRY with unexpected data type: {type(event.data)}")

        elif event.event_type == StreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
            if isinstance(event.data, AgentOperationalPhaseTransitionData):
                phase_value = event.data.new_phase.value
                tool_name = event.data.tool_name
                
                logger.info(f"[{self.cli_session_agent_id}] Agent phase transition: {phase_value}. Tool: {tool_name if tool_name else 'N/A'}.")
                
                phase_display_message = f"[Agent Status ({event_origin_agent_id}): {phase_value}"
                if tool_name:
                    phase_display_message += f" ({tool_name})"
                phase_display_message += "]"
                interactive_logger.info(phase_display_message)
            else:
                logger.warning(f"[{self.cli_session_agent_id}] Received AGENT_OPERATIONAL_PHASE_TRANSITION with unexpected data type: {type(event.data)}")

        elif event.event_type == StreamEventType.AGENT_IDLE:
            logger.info(f"[{self.cli_session_agent_id}] Agent is IDLE. Turn complete.")
            self.agent_turn_complete_event.set()

        elif event.event_type == StreamEventType.ERROR_EVENT:
            if isinstance(event.data, ErrorEventData):
                err_source = event.data.source 
                err_msg = event.data.message 
                interactive_logger.error(f"Stream Error ({event_origin_agent_id}, Source: {err_source}): {err_msg}")
            else:
                interactive_logger.error(f"Stream Error ({event_origin_agent_id}): {event.data}")
                logger.warning(f"[{self.cli_session_agent_id}] Received ERROR_EVENT with unexpected data type: {type(event.data)}")

            self.agent_turn_complete_event.set()
        
        else:
            logger.warning(f"[{self.cli_session_agent_id}] CLI Manager: Unhandled StreamEvent type: {event.event_type} with data type: {type(event.data)}")
            self.agent_turn_complete_event.set()


async def run(
    agent: Agent,
    show_tool_logs: bool = True,
    initial_prompt: Optional[str] = None
) -> None:
    if not isinstance(agent, Agent):
        raise TypeError(f"Expected an Agent instance, got {type(agent).__name__}")

    cli_session_agent_id = agent.agent_id 
    logger.info(f"agent_cli.run: Starting interactive session for agent '{cli_session_agent_id}'.")

    user_input_required_event = asyncio.Event()
    
    streamer = AgentEventStream(agent)
    cli_manager = InteractiveCLIManager(
        agent_turn_complete_event=user_input_required_event,
        show_tool_logs=show_tool_logs,
        cli_session_agent_id=cli_session_agent_id
    )
    
    event_processing_task: Optional[asyncio.Task] = None

    async def process_agent_events_loop():
        logger.debug("CLI process_agent_events_loop: Starting...")
        try:
            async for event in streamer.all_events():
                logger.debug(f"CLI process_agent_events_loop: Consumed event of type {event.event_type.value}")
                await cli_manager.handle_stream_event(event)
        except asyncio.CancelledError:
            logger.info(f"[{cli_session_agent_id}] CLI Event processing task cancelled.")
        except Exception as e_stream:
            logger.error(f"[{cli_session_agent_id}] CLI Error in event processing task: {e_stream}", exc_info=True)
        finally:
            logger.info(f"[{cli_session_agent_id}] CLI Event processing task stopped.")
            cli_manager._ensure_new_line()
            if not user_input_required_event.is_set():
                user_input_required_event.set()

    try:
        if not agent.is_running:
            agent.start()
        
        event_processing_task = asyncio.create_task(
            process_agent_events_loop(), 
            name=f"cli_event_processor_{cli_session_agent_id}"
        )
        
        logger.info(f"[{cli_session_agent_id}] Waiting for agent to initialize and become IDLE...")
        try:
            await asyncio.wait_for(user_input_required_event.wait(), timeout=30.0)
            logger.debug("CLI run: Initial wait for IDLE completed.")
        except asyncio.TimeoutError:
             logger.error(f"[{cli_session_agent_id}] Agent did not become IDLE within timeout. CLI may not function.")
             return

        if initial_prompt:
            logger.info(f"[{cli_session_agent_id}] Processing initial prompt: '{initial_prompt}'")
            cli_manager._ensure_new_line()
            interactive_logger.info(f"You: {initial_prompt}")
            user_input_required_event.clear()
            cli_manager.agent_has_spoken_this_turn = False
            await agent.post_user_message(AgentInputUserMessage(content=initial_prompt))
            await asyncio.sleep(0.01) # Yield control
            await user_input_required_event.wait()
            logger.debug("CLI run: Wait after initial prompt completed.")
        
        while True:
            user_input_required_event.clear()

            if cli_manager.pending_approval_invocation_id:
                try:
                    loop = asyncio.get_running_loop()
                    approval_input_str = await loop.run_in_executor(None, sys.stdin.readline)
                    approval_input_str = approval_input_str.strip().lower()
                except (EOFError, KeyboardInterrupt):
                    approval_input_str = "n"
                
                cli_manager._ensure_new_line()
                
                invocation_id_to_approve = cli_manager.pending_approval_invocation_id
                cli_manager.pending_approval_invocation_id = None

                if approval_input_str in ["yes", "y"]:
                    logger.info(f"[{cli_session_agent_id}] User approved tool invocation '{invocation_id_to_approve}'.")
                    await agent.post_tool_execution_approval(invocation_id_to_approve, is_approved=True, reason="User approved via CLI")
                else:
                    logger.info(f"[{cli_session_agent_id}] User denied tool invocation '{invocation_id_to_approve}'.")
                    await agent.post_tool_execution_approval(invocation_id_to_approve, is_approved=False, reason="User denied via CLI")
            
            else:
                cli_manager._ensure_new_line()
                if sys.stdout.isatty():
                    # Direct stdout write for the prompt to avoid newlines from logger
                    sys.stdout.write("You: ")
                    sys.stdout.flush()
                    cli_manager.current_line_empty = False
                
                try:
                    loop = asyncio.get_running_loop()
                    user_input_text = await loop.run_in_executor(None, sys.stdin.readline)
                    user_input_text = user_input_text.rstrip('\n')
                except (EOFError, KeyboardInterrupt):
                    logger.info(f"[{cli_session_agent_id}] EOF or Interrupt received, ending CLI session.")
                    break
                
                cli_manager._ensure_new_line()
                if not sys.stdout.isatty() and user_input_text: 
                    interactive_logger.info(f"You: {user_input_text}")

                if user_input_text.lower().strip() in ["/quit", "/exit"]:
                    logger.info(f"[{cli_session_agent_id}] Exit command received. Shutting down...")
                    break
                
                if not user_input_text.strip():
                    user_input_required_event.set()
                    continue
                
                cli_manager.agent_has_spoken_this_turn = False
                await agent.post_user_message(AgentInputUserMessage(content=user_input_text))
                await asyncio.sleep(0.01) # Yield control to allow event processor to start running

            await user_input_required_event.wait()
            logger.debug("CLI run: Wait at end of main loop completed.")

    except KeyboardInterrupt:
        logger.info(f"[{cli_session_agent_id}] KeyboardInterrupt received. Shutting down CLI session...")
    except Exception as e_main:
        logger.error(f"[{cli_session_agent_id}] An unhandled error occurred in the CLI main function: {e_main}", exc_info=True)
    finally:
        logger.info(f"[{cli_session_agent_id}] Cleaning up CLI session...")
        if event_processing_task and not event_processing_task.done():
            event_processing_task.cancel()
            try: await event_processing_task
            except asyncio.CancelledError: pass
            except Exception: pass
        if agent is not None and agent.is_running:
            logger.info(f"[{cli_session_agent_id}] Requesting agent to stop.")
            await agent.stop(timeout=5)
        if streamer and hasattr(streamer, 'close') and asyncio.iscoroutinefunction(streamer.close):
            try: 
                logger.debug(f"[{cli_session_agent_id}] Closing AgentEventStreamer.")
                await streamer.close()
            except Exception as e_close: 
                logger.error(f"[{cli_session_agent_id}] Error closing streamer: {e_close}", exc_info=True)
        cli_manager._ensure_new_line()
        logger.info(f"[{cli_session_agent_id}] Interactive session for agent '{cli_session_agent_id}' finished.")
