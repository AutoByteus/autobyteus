# file: autobyteus/autobyteus/cli/agent_cli.py
import asyncio
import logging
import sys
from typing import Optional, List

from autobyteus.agent.agent import Agent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.llm.utils.response_types import ChunkResponse

logger = logging.getLogger(__name__)

# Helper functions are now module-level (private by convention)
async def _listen_tool_logs(agent_id: str, streamer: AgentEventStream):
    """Internal helper to listen and print tool logs.
    Operational messages are logged, actual tool output is printed to stdout.
    """
    logger.debug(f"[{agent_id} TOOL_LOG_STREAM_START]")
    try:
        async for log_entry in streamer.stream_tool_logs():
            # Actual tool log content, keep printing to stdout for user visibility
            print(f"[{agent_id} Tool Log]: {log_entry}", flush=True)
    except asyncio.CancelledError:
        logger.debug(f"[{agent_id} TOOL_LOG_STREAM_CANCELLED]")
        logger.info(f"[{agent_id}] CLI Tool log listener cancelled.")
    except Exception as e_stream:
        # Log the error, no direct print to stdout as an error message
        logger.error(f"[{agent_id} TOOL_LOG_STREAM_ERROR: {e_stream}]", exc_info=True)
    finally:
        logger.info(f"[{agent_id}] CLI Tool log listener stopped.")

async def _listen_assistant_output(agent_id: str, streamer: AgentEventStream, responded_event: asyncio.Event):
    """Internal helper to listen and print assistant output.
    Signals responded_event upon completion or error.
    """
    logger.debug(f"[{agent_id} ASSISTANT_OUTPUT_STREAM_START]")
    try:
        async for chunk in streamer.stream_assistant_chunks():
            # Actual assistant output content, keep printing to stdout for user visibility
            if isinstance(chunk, ChunkResponse):
                print(chunk.content, end="", flush=True)
            else: 
                print(str(chunk), end="", flush=True) 
                logger.warning(f"[{agent_id}] CLI Assistant listener received unexpected chunk type: {type(chunk)}")
        # Ensure final flush after stream ends for complete output
        print(flush=True) 
    except asyncio.CancelledError:
        logger.debug(f"[{agent_id} ASSISTANT_OUTPUT_STREAM_CANCELLED]")
        logger.info(f"[{agent_id}] CLI Assistant output listener cancelled.")
    except Exception as e_stream:
        # Log the error, no direct print to stdout as an error message
        logger.error(f"[{agent_id} ASSISTANT_OUTPUT_STREAM_ERROR: {e_stream}]", exc_info=True)
    finally:
        # Ensure final flush even if error or cancellation, for visual cleanliness
        print(flush=True) 
        logger.info(f"[{agent_id}] CLI Assistant output listener stopped.")
        responded_event.set() # Signal that this response leg is complete

# Main public function of this module
async def run(
    agent: Agent,
    show_tool_logs: bool = True,
    initial_prompt: Optional[str] = None,
    initial_prompt_wait_time: float = 3.0 # This argument is now less critical for interactive mode
) -> None:
    """
    Runs an interactive Command Line Interface session for the given agent.

    This function handles starting the agent, listening to its outputs,
    prompting the user for input, and managing graceful shutdown.
    CLI operational messages are logged, while agent output and user prompts
    are printed to stdout for direct user interaction.

    Args:
        agent: The Agent instance to run interactively.
        show_tool_logs: If True, tool interaction logs will be printed to the console.
        initial_prompt: An optional initial message to send to the agent upon starting the session.
        initial_prompt_wait_time: (Largely informational) Time in seconds to wait after processing an
                                  initial_prompt. The CLI now waits for full response completion.
    """
    if not isinstance(agent, Agent):
        raise TypeError(f"Expected an Agent instance, got {type(agent).__name__}")

    agent_id_for_logs = agent.agent_id
    logger.info(f"agent_cli.run: Starting interactive session for agent '{agent_id_for_logs}'.")

    agent_responded_event = asyncio.Event()
    event_streamer = AgentEventStream(agent)
    tool_log_listener_task: Optional[asyncio.Task] = None
    assistant_output_listener_task: Optional[asyncio.Task] = None
    
    try:
        if not agent.is_running:
            agent.start()
            await asyncio.sleep(0.1) 

        assistant_output_listener_task = asyncio.create_task(
            _listen_assistant_output(agent_id_for_logs, event_streamer, agent_responded_event),
            name=f"cli_assistant_listener_{agent_id_for_logs}"
        )
        if show_tool_logs:
            tool_log_listener_task = asyncio.create_task(
                _listen_tool_logs(agent_id_for_logs, event_streamer),
                name=f"cli_tool_log_listener_{agent_id_for_logs}"
            )

        await asyncio.sleep(0.1) 

        logger.info(f"Agent '{agent_id_for_logs}' is ready. Type your message or '/quit' to exit.")

        if initial_prompt:
            logger.info(f"[{agent_id_for_logs}] Processing initial prompt: '{initial_prompt}'")
            initial_message = AgentInputUserMessage(content=initial_prompt)
            
            agent_responded_event.clear()
            await agent.post_user_message(initial_message)
            
            logger.debug(f"[{agent_id_for_logs}] CLI initial prompt: Waiting for agent response signal...")
            await agent_responded_event.wait()
            logger.debug(f"[{agent_id_for_logs}] CLI initial prompt: Agent response signal received.")
            if initial_prompt_wait_time > 0: # Keep for compatibility or specific non-interactive uses
                 logger.debug(f"Initial prompt processed, optional wait time specified: {initial_prompt_wait_time}s (now largely symbolic for interactive mode as full response is awaited).")
        
        # Initial prompt for interactive mode after any initial_prompt is handled
        if sys.stdout.isatty():
            print("You: ", end="", flush=True)

        while True:
            try:
                user_input_text = await asyncio.to_thread(sys.stdin.readline)
                user_input_text = user_input_text.rstrip('\n')
                
                if not sys.stdout.isatty() and user_input_text: 
                    print(f"You: {user_input_text}", flush=True)

            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e) or "must be run in a worker thread" in str(e):
                    loop = asyncio.get_running_loop()
                    user_input_text = await loop.run_in_executor(None, sys.stdin.readline)
                    user_input_text = user_input_text.rstrip('\n')
                    if not sys.stdout.isatty() and user_input_text:
                         print(f"You: {user_input_text}", flush=True)
                else:
                    logger.error(f"Error reading user input: {e}", exc_info=True)
                    break 
            except EOFError:
                logger.info("EOF received, ending CLI session.")
                break

            if user_input_text.lower().strip() in ["/quit", "/exit"]:
                logger.info(f"[{agent_id_for_logs}] Exit command received. Shutting down CLI session...")
                break
            
            if not user_input_text.strip():
                # If input is empty, just continue. The prompt from the previous completed interaction remains.
                continue
            
            message = AgentInputUserMessage(content=user_input_text)
            agent_responded_event.clear() # Clear before posting, ready for the new response
            await agent.post_user_message(message)
            
            logger.debug(f"[{agent_id_for_logs}] CLI main loop: Waiting for agent response signal...")
            await agent_responded_event.wait() # Wait for the agent to finish responding
            logger.debug(f"[{agent_id_for_logs}] CLI main loop: Agent response signal received.")
            
            if sys.stdout.isatty(): 
                print("You: ", end="", flush=True) # Re-prompt only after response is complete

    except KeyboardInterrupt:
        logger.info(f"[{agent_id_for_logs}] KeyboardInterrupt received. Shutting down CLI session...")
        logger.info("CLI session exiting...")
    except Exception as e_main:
        logger.error(f"[{agent_id_for_logs}] An error occurred in the CLI session: {e_main}", exc_info=True)
        logger.error(f"An error occurred: {e_main}", exc_info=True)
    finally:
        logger.info(f"[{agent_id_for_logs}] Cleaning up CLI session...")
        
        tasks_to_cancel: List[Optional[asyncio.Task]] = []
        # Important: assistant_output_listener_task sets the event, ensure it can finish or be cancelled cleanly.
        # If it's cancelled before setting the event, the main loop might hang if not handled.
        # The `finally` block in _listen_assistant_output ensures event.set() is called.
        if assistant_output_listener_task and not assistant_output_listener_task.done():
            assistant_output_listener_task.cancel()
            tasks_to_cancel.append(assistant_output_listener_task)
        if tool_log_listener_task and not tool_log_listener_task.done():
            tool_log_listener_task.cancel()
            tasks_to_cancel.append(tool_log_listener_task)

        if tasks_to_cancel:
            await asyncio.gather(*[t for t in tasks_to_cancel if t], return_exceptions=True)
            logger.debug(f"[{agent_id_for_logs}] Listener tasks cancellation attempted.")

        if agent.is_running:
            logger.info(f"[{agent_id_for_logs}] Stopping agent runtime...")
            await agent.stop(timeout=15) # Give enough time for graceful agent shutdown
        
        logger.info(f"[{agent_id_for_logs}] Interactive session for agent '{agent_id_for_logs}' finished.")
        logger.info(f"Agent '{agent_id_for_logs}' session ended.")
