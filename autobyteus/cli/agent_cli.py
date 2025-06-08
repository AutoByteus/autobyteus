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
    EmptyData # Though less likely to be directly checked unless specific logic for it
)
from autobyteus.agent.context.phases import AgentOperationalPhase 

logger = logging.getLogger(__name__) 

class InteractiveCLIManager:
    """
    Manages the state and rendering logic for the interactive CLI session.
    """
    def __init__(self, 
                 agent: Agent, 
                 agent_turn_complete_event: asyncio.Event, 
                 show_tool_logs: bool,
                 cli_session_agent_id: str):
        self.agent = agent
        self.agent_turn_complete_event = agent_turn_complete_event
        self.show_tool_logs = show_tool_logs
        self.cli_session_agent_id = cli_session_agent_id

        self.current_line_empty: bool = True
        self.agent_has_spoken_this_turn: bool = False 

    def _ensure_new_line(self):
        """Ensures the cursor is on a new line if the current one isn't empty."""
        if not self.current_line_empty:
            print(flush=True) # Will print a newline
            self.current_line_empty = True

    async def _prompt_tool_approval(self, tool_approval_payload: ToolInvocationApprovalRequestedData): # MODIFIED: Typed payload
        """Handles the logic for prompting user for tool approval."""
        # Access attributes directly from the Pydantic model
        invocation_id = tool_approval_payload.invocation_id
        tool_name = tool_approval_payload.tool_name
        arguments = tool_approval_payload.arguments
        # event_agent_id can be taken from the StreamEvent.agent_id if needed,
        # or assume it's self.cli_session_agent_id if payload doesn't carry it.
        # For now, we assume event.agent_id in handle_stream_event covers this.
        event_agent_id = self.cli_session_agent_id # Fallback, or get from StreamEvent's agent_id

        if not all([invocation_id, tool_name is not None]):  # pragma: no cover
            logger.error(f"[{event_agent_id}] Invalid data for tool approval request: {tool_approval_payload}")
            self.current_line_empty = True 
            return

        try:
            args_str = json.dumps(arguments, indent=2)
        except TypeError: # pragma: no cover
            args_str = str(arguments)

        self._ensure_new_line()

        prompt_message = (
            f"Tool Call ({event_agent_id}): '{tool_name}' (Invocation ID: {invocation_id}) requests permission to run with arguments:\n"
            f"{args_str}\nApprove? (y/n): " 
        )
        print(prompt_message, end="", flush=True)
        self.current_line_empty = False

        try:
            loop = asyncio.get_running_loop()
            approval_input_str = await loop.run_in_executor(None, sys.stdin.readline)
            approval_input_str = approval_input_str.strip().lower()
        except EOFError: # pragma: no cover
            logger.warning(f"[{event_agent_id}] EOF received while awaiting tool approval for '{tool_name}'. Denying request.")
            approval_input_str = "n" 
        except Exception as e: # pragma: no cover
            logger.error(f"[{event_agent_id}] Error reading tool approval input for '{tool_name}': {e}. Denying request.", exc_info=True)
            approval_input_str = "n" 
        
        print() 
        self.current_line_empty = True 

        if approval_input_str in ["yes", "y"]: 
            logger.info(f"[{event_agent_id}] User approved tool '{tool_name}' (ID: {invocation_id}).")
            await self.agent.post_tool_execution_approval(invocation_id, is_approved=True, reason="User approved via CLI")
        else: 
            logger.info(f"[{event_agent_id}] User denied tool '{tool_name}' (ID: {invocation_id}). Input: '{approval_input_str}'")
            await self.agent.post_tool_execution_approval(invocation_id, is_approved=False, reason=f"User denied via CLI (input: '{approval_input_str}')")

    async def handle_stream_event(self, event: StreamEvent):
        """Processes a single StreamEvent and updates the CLI display."""
        event_origin_agent_id = event.agent_id or self.cli_session_agent_id

        if event.event_type != StreamEventType.ASSISTANT_CHUNK:
            self._ensure_new_line()
            if event.event_type not in [StreamEventType.ASSISTANT_COMPLETE_RESPONSE]: # Renamed from ASSISTANT_FINAL_MESSAGE
                 self.agent_has_spoken_this_turn = False


        if event.event_type == StreamEventType.ASSISTANT_CHUNK:
            if isinstance(event.data, AssistantChunkData):
                chunk_content = event.data.content # Access attribute
                if not self.agent_has_spoken_this_turn:
                    print(f"Agent ({event_origin_agent_id}): ", end="", flush=True)
                    self.agent_has_spoken_this_turn = True
                    self.current_line_empty = False 
                
                print(chunk_content, end="", flush=True)
                if chunk_content.endswith('\n'):
                    self.current_line_empty = True
                else:
                    self.current_line_empty = False
            else: # pragma: no cover
                logger.warning(f"[{self.cli_session_agent_id}] Received ASSISTANT_CHUNK with unexpected data type: {type(event.data)}")


        elif event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE: # RENAMED
            if isinstance(event.data, AssistantCompleteResponseData): # Check type
                complete_resp_content = event.data.content # Access attribute
                content_printed_this_event = False

                if not self.agent_has_spoken_this_turn and complete_resp_content:
                    print(f"Agent ({event_origin_agent_id}): {complete_resp_content}", flush=True)
                    content_printed_this_event = True
                elif self.agent_has_spoken_this_turn and not self.current_line_empty:
                    # This means chunks were printed without a final newline
                    print(flush=True) # Finish the line from chunks
                
                logger.debug(f"[{self.cli_session_agent_id}] Received ASSISTANT_COMPLETE_RESPONSE. Content printed: {content_printed_this_event}, Content: '{complete_resp_content[:100]}...'")
                self.current_line_empty = True 
            else: # pragma: no cover
                 logger.warning(f"[{self.cli_session_agent_id}] Received ASSISTANT_COMPLETE_RESPONSE with unexpected data type: {type(event.data)}")


        elif event.event_type == StreamEventType.TOOL_APPROVAL_REQUESTED:
            if isinstance(event.data, ToolInvocationApprovalRequestedData): # Check type
                logger.debug(f"[{self.cli_session_agent_id}] Handling TOOL_APPROVAL_REQUESTED event. Data: {event.data}")
                await self._prompt_tool_approval(event.data) # Pass the typed payload
            else: # pragma: no cover
                logger.warning(f"[{self.cli_session_agent_id}] Received TOOL_APPROVAL_REQUESTED with unexpected data type: {type(event.data)}")
            self.agent_has_spoken_this_turn = False 

        elif event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            if isinstance(event.data, ToolInteractionLogEntryData): # Check type
                if self.show_tool_logs:
                    print(f"Tool Log ({event_origin_agent_id}): {event.data.log_entry}", flush=True) # Access attribute
            else: # pragma: no cover
                logger.warning(f"[{self.cli_session_agent_id}] Received TOOL_INTERACTION_LOG_ENTRY with unexpected data type: {type(event.data)}")
            self.current_line_empty = True 
            self.agent_has_spoken_this_turn = False

        elif event.event_type == StreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
            if isinstance(event.data, AgentOperationalPhaseTransitionData):
                phase_value = event.data.new_phase.value
                tool_name = event.data.tool_name
                
                logger.info(f"[{self.cli_session_agent_id}] Agent phase transition: {phase_value}. Tool: {tool_name if tool_name else 'N/A'}.")
                
                phase_display_message = f"[Agent Status ({event_origin_agent_id}): {phase_value}"
                if tool_name:
                    phase_display_message += f" ({tool_name})"
                phase_display_message += "]"

                print(phase_display_message, flush=True)
                self.current_line_empty = True
                
                self.agent_has_spoken_this_turn = False
            else: # pragma: no cover
                logger.warning(f"[{self.cli_session_agent_id}] Received AGENT_OPERATIONAL_PHASE_TRANSITION with unexpected data type: {type(event.data)}")

        elif event.event_type == StreamEventType.AGENT_IDLE:
            # This event now signals the end of a turn.
            logger.info(f"[{self.cli_session_agent_id}] Agent is IDLE. Turn complete.")
            self._ensure_new_line()
            self.agent_has_spoken_this_turn = False
            self.agent_turn_complete_event.set()

        elif event.event_type == StreamEventType.ERROR_EVENT:
            if isinstance(event.data, ErrorEventData): # Check type
                err_source = event.data.source 
                err_msg = event.data.message 
                print(f"Stream Error ({event_origin_agent_id}, Source: {err_source}): {err_msg}", flush=True)
            else: # pragma: no cover
                print(f"Stream Error ({event_origin_agent_id}): {event.data}", flush=True) # Fallback for unexpected data
                logger.warning(f"[{self.cli_session_agent_id}] Received ERROR_EVENT with unexpected data type: {type(event.data)}")

            self.current_line_empty = True 
            self.agent_has_spoken_this_turn = False
            self.agent_turn_complete_event.set() 
        
        else: # pragma: no cover
            logger.warning(f"[{self.cli_session_agent_id}] CLI Manager: Unhandled StreamEvent type: {event.event_type} with data type: {type(event.data)}")
            self.current_line_empty = True 
            self.agent_has_spoken_this_turn = False


async def run(
    agent: Agent,
    show_tool_logs: bool = True,
    initial_prompt: Optional[str] = None
) -> None: # pragma: no cover 
    if not isinstance(agent, Agent):
        raise TypeError(f"Expected an Agent instance, got {type(agent).__name__}")

    cli_session_agent_id = agent.agent_id 
    logger.info(f"agent_cli.run: Starting interactive session for agent '{cli_session_agent_id}'.")

    agent_turn_complete_event = asyncio.Event()
    streamer = AgentEventStream(agent)
    
    cli_manager = InteractiveCLIManager(
        agent=agent,
        agent_turn_complete_event=agent_turn_complete_event,
        show_tool_logs=show_tool_logs,
        cli_session_agent_id=cli_session_agent_id
    )
    
    event_processing_task: Optional[asyncio.Task] = None

    async def process_agent_events_loop():
        try:
            async for event in streamer.all_events():
                await cli_manager.handle_stream_event(event)
        except asyncio.CancelledError:
            logger.info(f"[{cli_session_agent_id}] CLI Event processing task cancelled.")
        except Exception as e_stream:
            logger.error(f"[{cli_session_agent_id}] CLI Error in event processing task: {e_stream}", exc_info=True)
        finally:
            logger.info(f"[{cli_session_agent_id}] CLI Event processing task stopped.")
            cli_manager._ensure_new_line()
            cli_manager.agent_has_spoken_this_turn = False
            if not agent_turn_complete_event.is_set():
                agent_turn_complete_event.set() 

    try:
        if not agent.is_running:
            agent.start()
            logger.info(f"[{cli_session_agent_id}] Waiting for agent to initialize and become IDLE...")
            
            event_processing_task = asyncio.create_task(
                process_agent_events_loop(), 
                name=f"cli_event_processor_{cli_session_agent_id}"
            )
            
            try:
                await asyncio.wait_for(agent_turn_complete_event.wait(), timeout=30.0)
                agent_turn_complete_event.clear() 
                logger.info(f"[{cli_session_agent_id}] Agent confirmed IDLE. CLI ready.")
            except asyncio.TimeoutError:
                 logger.error(f"[{cli_session_agent_id}] Agent did not become IDLE within timeout during startup. CLI may not function correctly.")
        else: # Agent already running
            event_processing_task = asyncio.create_task(
                process_agent_events_loop(), 
                name=f"cli_event_processor_{cli_session_agent_id}"
            )


        logger.info(f"Agent ({cli_session_agent_id}) is ready. Type your message or '/quit' to exit.")

        if initial_prompt:
            logger.info(f"[{cli_session_agent_id}] Processing initial prompt: '{initial_prompt}'")
            cli_manager._ensure_new_line()
            print(f"You: {initial_prompt}", flush=True) 
            cli_manager.current_line_empty = True 
            
            agent_turn_complete_event.clear()
            cli_manager.agent_has_spoken_this_turn = False 
            await agent.post_user_message(AgentInputUserMessage(content=initial_prompt))
            await agent_turn_complete_event.wait() 
        
        while True:
            cli_manager._ensure_new_line()
            
            if sys.stdout.isatty(): 
                print("You: ", end="", flush=True)
                cli_manager.current_line_empty = False 
            
            try:
                loop = asyncio.get_running_loop()
                user_input_text = await loop.run_in_executor(None, sys.stdin.readline)
                user_input_text = user_input_text.rstrip('\n') 
                cli_manager.current_line_empty = True 
                if not sys.stdout.isatty() and user_input_text: 
                    print(f"You: {user_input_text}", flush=True)
            except EOFError: 
                logger.info(f"[{cli_session_agent_id}] EOF received, ending CLI session.")
                cli_manager._ensure_new_line()
                break
            except Exception as e: 
                logger.error(f"[{cli_session_agent_id}] Error reading user input: {e}", exc_info=True)
                cli_manager._ensure_new_line()
                break 

            if user_input_text.lower().strip() in ["/quit", "/exit"]:
                logger.info(f"[{cli_session_agent_id}] Exit command received. Shutting down CLI session...")
                break
            
            if not user_input_text.strip(): 
                continue 
            
            agent_turn_complete_event.clear() 
            cli_manager.agent_has_spoken_this_turn = False 
            await agent.post_user_message(AgentInputUserMessage(content=user_input_text))
            await agent_turn_complete_event.wait() 
            
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
