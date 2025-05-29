# file: autobyteus/autobyteus/cli/agent_cli.py
import asyncio
import logging
import sys
from typing import Optional, List, Dict, Any
import json # For pretty printing arguments

from autobyteus.agent.agent import Agent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType

logger = logging.getLogger(__name__)

async def _handle_tool_approval_request(agent: Agent, event_data: Dict[str, Any]):
    """Handles the logic for prompting user for tool approval."""
    invocation_id = event_data.get("invocation_id")
    tool_name = event_data.get("tool_name")
    arguments = event_data.get("arguments", {})
    agent_id_for_logs = event_data.get("agent_id", agent.agent_id)

    if not all([invocation_id, tool_name]):
        logger.error(f"[{agent_id_for_logs}] Invalid TOOL_APPROVAL_REQUESTED event data: {event_data}")
        return

    try:
        args_str = json.dumps(arguments, indent=2)
    except TypeError:
        args_str = str(arguments)

    # Removed leading \n, relies on main loop's formatting
    prompt_message = (
        f"[{agent_id_for_logs}] Tool '{tool_name}' (Invocation ID: {invocation_id}) requests permission to run with arguments:\n"
        f"{args_str}\nApprove? (yes/no/y/n): "
    )
    print(prompt_message, end="", flush=True)

    try:
        loop = asyncio.get_running_loop()
        approval_input = await loop.run_in_executor(None, sys.stdin.readline)
        approval_input = approval_input.strip().lower()
    except EOFError:
        logger.warning(f"[{agent_id_for_logs}] EOF received while awaiting tool approval. Denying request.")
        approval_input = "no"
    except Exception as e:
        logger.error(f"[{agent_id_for_logs}] Error reading tool approval input: {e}. Denying request.", exc_info=True)
        approval_input = "no"


    if approval_input in ["yes", "y"]:
        logger.info(f"[{agent_id_for_logs}] User approved tool '{tool_name}' (ID: {invocation_id}).")
        await agent.post_tool_execution_approval(invocation_id, is_approved=True, reason="User approved via CLI")
    else:
        logger.info(f"[{agent_id_for_logs}] User denied tool '{tool_name}' (ID: {invocation_id}). Input: '{approval_input}'")
        await agent.post_tool_execution_approval(invocation_id, is_approved=False, reason=f"User denied via CLI (input: '{approval_input}')")
    
async def run(
    agent: Agent,
    show_tool_logs: bool = True,
    initial_prompt: Optional[str] = None
) -> None:
    """
    Runs an interactive Command Line Interface session for the given agent.
    The CLI reacts to a unified stream of events from the agent.

    Args:
        agent: The Agent instance to run interactively.
        show_tool_logs: If True, tool interaction logs will be printed to the console.
        initial_prompt: An optional initial message to send to the agent upon starting the session.
    """
    if not isinstance(agent, Agent):
        raise TypeError(f"Expected an Agent instance, got {type(agent).__name__}")

    agent_id_for_logs = agent.agent_id
    logger.info(f"agent_cli.run: Starting interactive session for agent '{agent_id_for_logs}'.")

    agent_turn_complete_event = asyncio.Event()
    streamer = AgentEventStream(agent)
    
    event_processing_task: Optional[asyncio.Task] = None

    async def process_agent_events():
        nonlocal agent_turn_complete_event
        current_line_empty = True 
        try:
            async for event in streamer.all_events():
                # Generic newline handler: if current line isn't empty (due to prior chunk without \n)
                # and this event isn't a chunk itself, print a newline first.
                if not current_line_empty and event.event_type not in [StreamEventType.ASSISTANT_CHUNK]:
                    print(flush=True) # Finishes the previous line
                    current_line_empty = True # The current line is now conceptually empty

                if event.event_type == StreamEventType.ASSISTANT_CHUNK:
                    chunk_content = event.data.get("chunk", "")
                    print(chunk_content, end="", flush=True)
                    current_line_empty = chunk_content.endswith('\n')
                elif event.event_type == StreamEventType.ASSISTANT_FINAL_MESSAGE:
                    # Redundant newline check removed, generic one above handles it.
                    logger.debug(f"[{agent_id_for_logs}] CLI: Received ASSISTANT_FINAL_MESSAGE. Signal turn complete.")
                    agent_turn_complete_event.set()
                    current_line_empty = True 
                elif event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY:
                    if show_tool_logs:
                        print(f"[{agent_id_for_logs} Tool Log]: {event.data.get('log_line', '')}", flush=True)
                    current_line_empty = True 
                elif event.event_type == StreamEventType.TOOL_APPROVAL_REQUESTED:
                    await _handle_tool_approval_request(agent, event.data)
                    current_line_empty = True 
                elif event.event_type == StreamEventType.ERROR_EVENT:
                    err_source = event.data.get('source_stream', 'Unknown')
                    err_msg = event.data.get('error', 'An unknown error occurred in stream.')
                    # Removed leading \n, relies on main loop's formatting
                    print(f"[{agent_id_for_logs} Stream Error from {err_source}]: {err_msg}", flush=True)
                    agent_turn_complete_event.set() 
                    current_line_empty = True
                else:
                    logger.warning(f"[{agent_id_for_logs}] CLI: Unhandled StreamEvent type: {event.event_type}")
                    current_line_empty = True # Assume unhandled events end the line

        except asyncio.CancelledError:
            logger.info(f"[{agent_id_for_logs}] CLI Event processing task cancelled.")
        except Exception as e_stream:
            logger.error(f"[{agent_id_for_logs}] CLI Error in event processing task: {e_stream}", exc_info=True)
        finally:
            logger.info(f"[{agent_id_for_logs}] CLI Event processing task stopped.")
            if not agent_turn_complete_event.is_set():
                agent_turn_complete_event.set() # Ensure main loop can unblock if task ends unexpectedly

    try:
        if not agent.is_running:
            agent.start()
            await asyncio.sleep(0.2) # Give runtime a moment to initialize

        event_processing_task = asyncio.create_task(
            process_agent_events(), 
            name=f"cli_event_processor_{agent_id_for_logs}"
        )
        await asyncio.sleep(0.1) # Allow event processor task to start and potentially process initial status

        logger.info(f"Agent '{agent_id_for_logs}' is ready. Type your message or '/quit' to exit.")

        if initial_prompt:
            logger.info(f"[{agent_id_for_logs}] Processing initial prompt: '{initial_prompt}'")
            initial_message = AgentInputUserMessage(content=initial_prompt)
            
            agent_turn_complete_event.clear()
            await agent.post_user_message(initial_message)
            
            logger.debug(f"[{agent_id_for_logs}] CLI initial prompt: Waiting for agent turn to complete...")
            await agent_turn_complete_event.wait()
            logger.debug(f"[{agent_id_for_logs}] CLI initial prompt: Agent turn complete.")
        
        while True:
            if sys.stdout.isatty(): # Only print "You: " prompt in interactive TTY
                print("You: ", end="", flush=True)
            
            try:
                loop = asyncio.get_running_loop()
                user_input_text = await loop.run_in_executor(None, sys.stdin.readline)
                user_input_text = user_input_text.rstrip('\n') # Remove trailing newline
                
                # If not a TTY (e.g., piped input), echo the input for clarity
                if not sys.stdout.isatty() and user_input_text: 
                    print(f"You: {user_input_text}", flush=True)

            except EOFError: # Typically Ctrl+D
                logger.info(f"[{agent_id_for_logs}] EOF received, ending CLI session.")
                break
            except Exception as e: # Catch other potential errors from input reading
                logger.error(f"[{agent_id_for_logs}] Error reading user input: {e}", exc_info=True)
                break 

            if user_input_text.lower().strip() in ["/quit", "/exit"]:
                logger.info(f"[{agent_id_for_logs}] Exit command received. Shutting down CLI session...")
                break
            
            if not user_input_text.strip(): # Ignore empty lines
                continue 
            
            message = AgentInputUserMessage(content=user_input_text)
            agent_turn_complete_event.clear() # Reset for the new turn
            await agent.post_user_message(message)
            
            logger.debug(f"[{agent_id_for_logs}] CLI main loop: Waiting for agent turn to complete...")
            await agent_turn_complete_event.wait() # Wait for agent to finish its response cycle
            logger.debug(f"[{agent_id_for_logs}] CLI main loop: Agent turn complete.")

    except KeyboardInterrupt:
        logger.info(f"[{agent_id_for_logs}] KeyboardInterrupt received. Shutting down CLI session...")
    except Exception as e_main:
        logger.error(f"[{agent_id_for_logs}] An unhandled error occurred in the CLI main function: {e_main}", exc_info=True)
    finally:
        logger.info(f"[{agent_id_for_logs}] Cleaning up CLI session...")
        
        if event_processing_task and not event_processing_task.done():
            event_processing_task.cancel()
            try:
                await event_processing_task
            except asyncio.CancelledError:
                logger.debug(f"[{agent_id_for_logs}] Event processing task successfully cancelled.")
            except Exception as e_cancel: # pragma: no cover
                logger.error(f"[{agent_id_for_logs}] Error during event_processing_task cleanup: {e_cancel}", exc_info=True)

        if agent.is_running:
            logger.info(f"[{agent_id_for_logs}] Stopping agent runtime...")
            await agent.stop(timeout=15) # Increased timeout slightly for potentially busy agents
        
        if hasattr(streamer, 'close') and asyncio.iscoroutinefunction(streamer.close):
            try:
                await streamer.close()
            except Exception as e_streamer_close: # pragma: no cover
                logger.error(f"Error closing AgentEventStream: {e_streamer_close}", exc_info=True)
        
        logger.info(f"[{agent_id_for_logs}] Interactive session for agent '{agent_id_for_logs}' finished.")
