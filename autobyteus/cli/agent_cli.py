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
from autobyteus.agent.phases import AgentOperationalPhase 

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
        self.agent_has_spoken_this_turn: bool = False # Tracks if "Agent:" prefix was printed

    def _ensure_new_line(self):
        """Ensures the cursor is on a new line if the current one isn't empty."""
        if not self.current_line_empty:
            print(flush=True)
            self.current_line_empty = True

    async def _prompt_tool_approval(self, tool_approval_data: Dict[str, Any]):
        """Handles the logic for prompting user for tool approval."""
        invocation_id = tool_approval_data.get("invocation_id")
        tool_name = tool_approval_data.get("tool_name")
        arguments = tool_approval_data.get("arguments", {})
        event_agent_id = tool_approval_data.get("agent_id", self.agent.agent_id)

        if not all([invocation_id, tool_name is not None]):  # pragma: no cover
            logger.error(f"[{event_agent_id}] Invalid data for tool approval request: {tool_approval_data}")
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
        # self.current_line_empty is False because prompt doesn't end with newline

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
        
        print() # Add a newline after user types their y/n and hits enter
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

        # Most events imply the agent is "speaking" or providing info,
        # so ensure a new line unless it's a continuation chunk.
        if event.event_type != StreamEventType.ASSISTANT_CHUNK:
            self._ensure_new_line()
            # Reset agent_has_spoken_this_turn for most events.
            # It's specifically managed for CHUNK/FINAL_MESSAGE.
            if event.event_type not in [StreamEventType.ASSISTANT_FINAL_MESSAGE]:
                 self.agent_has_spoken_this_turn = False


        if event.event_type == StreamEventType.ASSISTANT_CHUNK:
            chunk_content = event.data.get("chunk", "")
            if not self.agent_has_spoken_this_turn:
                print(f"Agent ({event_origin_agent_id}): ", end="", flush=True)
                self.agent_has_spoken_this_turn = True
                self.current_line_empty = False 
            
            print(chunk_content, end="", flush=True)
            if chunk_content.endswith('\n'):
                self.current_line_empty = True
            else:
                self.current_line_empty = False

        elif event.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE:
            final_msg_content = event.data.get("message", "")
            content_printed_this_event = False

            if not self.agent_has_spoken_this_turn and final_msg_content:
                print(f"Agent ({event_origin_agent_id}): {final_msg_content}", flush=True)
                content_printed_this_event = True
            elif self.agent_has_spoken_this_turn and not self.current_line_empty:
                print(flush=True) # Finish the line from chunks
            
            logger.debug(f"[{self.cli_session_agent_id}] Received ASSISTANT_FINAL_MESSAGE. Content printed: {content_printed_this_event}, Content: '{final_msg_content[:100]}...'")
            self.current_line_empty = True 
            # self.agent_has_spoken_this_turn will be reset by IDLE phase or next user input cycle.

        elif event.event_type == StreamEventType.TOOL_APPROVAL_REQUESTED:
            logger.debug(f"[{self.cli_session_agent_id}] Handling TOOL_APPROVAL_REQUESTED event. Data: {event.data}")
            await self._prompt_tool_approval(event.data)
            self.agent_has_spoken_this_turn = False # Tool approval is not agent "speaking"

        elif event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY:
            if self.show_tool_logs:
                print(f"Tool Log ({event_origin_agent_id}): {event.data.get('log_line', '')}", flush=True)
            self.current_line_empty = True 
            self.agent_has_spoken_this_turn = False

        elif event.event_type == StreamEventType.AGENT_PHASE_UPDATE:
            phase = event.data.get('phase')
            logger.info(f"[{self.cli_session_agent_id}] Agent phase: {phase}. Data in event: {list(event.data.keys())}")
            
            if phase and phase != AgentOperationalPhase.IDLE.value:
                print(f"[Agent Status ({event_origin_agent_id}): {phase}]", flush=True)
                self.current_line_empty = True 
            
            self.agent_has_spoken_this_turn = False 

            if phase == AgentOperationalPhase.IDLE.value:
                logger.info(f"[{self.cli_session_agent_id}] Agent entered IDLE phase. Turn complete.")
                self._ensure_new_line() # Ensure any previous agent output is newline-terminated
                self.agent_has_spoken_this_turn = False 
                self.agent_turn_complete_event.set()

        elif event.event_type == StreamEventType.ERROR_EVENT:
            err_source = event.data.get('source_stream', 'Unknown')
            err_msg = event.data.get('error', 'An unknown error occurred in stream.')
            print(f"Stream Error ({event_origin_agent_id}, Source: {err_source}): {err_msg}", flush=True)
            self.current_line_empty = True 
            self.agent_has_spoken_this_turn = False
            self.agent_turn_complete_event.set() 
        
        else: # Should not happen
            logger.warning(f"[{self.cli_session_agent_id}] CLI Manager: Unhandled StreamEvent type: {event.event_type}")
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
    
    # Create the CLI Manager instance
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
            initial_idle_event = asyncio.Event()
            
            # Use a temporary streamer for initial idle check to avoid consuming events meant for main processor
            # OR rely on the main cli_manager to handle initial phase updates appropriately.
            # For simplicity, we'll let the main event processor start and handle initial phases.
            # The `wait_for_initial_idle` logic below uses the main streamer.
            
            async def wait_for_initial_idle_using_main_streamer():
                # This function will now be simpler as handle_stream_event does the printing
                async for event in streamer.all_events():
                    await cli_manager.handle_stream_event(event) # Let manager print status
                    if event.event_type == StreamEventType.AGENT_PHASE_UPDATE and \
                       event.data.get('phase') == AgentOperationalPhase.IDLE.value:
                        logger.info(f"[{cli_session_agent_id}] Agent confirmed IDLE. CLI ready.")
                        initial_idle_event.set()
                        return # Stop this temporary listener task
                    elif event.event_type == StreamEventType.ERROR_EVENT:
                        logger.error(f"[{cli_session_agent_id}] Error during agent initialization: {event.data.get('error')}")
                        initial_idle_event.set() 
                        return 
            
            # Start the main event processing task, it will handle initial phase messages.
            event_processing_task = asyncio.create_task(
                process_agent_events_loop(), 
                name=f"cli_event_processor_{cli_session_agent_id}"
            )
            
            # Wait for the first IDLE event specifically for readiness before initial prompt
            # This requires a way to "peek" or wait for a specific condition without fully consuming the main stream loop
            # The original wait_for_initial_idle consuming `streamer.all_events()` was problematic as it would steal events
            # from the main `process_agent_events_loop`.
            # A simpler approach: The main loop will set agent_turn_complete_event when IDLE.
            # We just need to wait for that.
            
            # Wait for the agent to become IDLE the first time.
            # The `process_agent_events_loop` will set `agent_turn_complete_event` upon first IDLE.
            try:
                await asyncio.wait_for(agent_turn_complete_event.wait(), timeout=30.0)
                agent_turn_complete_event.clear() # Clear for subsequent turns
                logger.info(f"[{cli_session_agent_id}] Agent confirmed IDLE. CLI ready.")
            except asyncio.TimeoutError:
                 logger.error(f"[{cli_session_agent_id}] Agent did not become IDLE within timeout during startup. CLI may not function correctly.")
                 # The event_processing_task will continue running or fail based on agent's state.


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

