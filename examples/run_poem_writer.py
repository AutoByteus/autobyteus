import asyncio
import logging
import argparse
from pathlib import Path
import tempfile
import sys
import os

# Ensure the autobyteus package is discoverable if running script from examples dir directly
# This assumes the script is in autobyteus/examples and the package root is autobyteus/
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT)) # Add project root (e.g., 'autobyteus_project/') to path

try:
    from autobyteus.agent.registry.agent_definition import AgentDefinition
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
    from autobyteus.llm.models import LLMModel
    from autobyteus.agent.registry.agent_registry import default_agent_registry
    from autobyteus.agent.agent import Agent
    from autobyteus.agent.status import AgentStatus 
    from autobyteus.agent.streaming.agent_output_streams import AgentOutputStreams
except ImportError as e:
    print(f"Error importing autobyteus components: {e}")
    print("Please ensure that the autobyteus library is installed and accessible in your PYTHONPATH.")
    print(f"Attempted to add to sys.path: {str(PACKAGE_ROOT.parent)}")
    sys.exit(1)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("run_poem_writer")

async def listen_to_tool_logs(agent_id: str, streams: AgentOutputStreams):
    """Listens to and prints tool interaction logs from the agent."""
    # Using print for immediate visibility for example script
    # Consider directing to logger if script becomes more complex or used in automation
    print(f"\n[{agent_id} TOOL_LOG_STREAM_START]", flush=True)
    try:
        async for log_entry in streams.stream_tool_interaction_logs():
            print(f"[{agent_id} TOOL_LOG] {log_entry}", flush=True)
    except asyncio.CancelledError:
        print(f"\n[{agent_id} TOOL_LOG_STREAM_CANCELLED]", flush=True)
        logger.info(f"[{agent_id}] Tool log listener cancelled.")
    except Exception as e:
        print(f"\n[{agent_id} TOOL_LOG_STREAM_ERROR]", flush=True)
        logger.error(f"[{agent_id}] Error in tool log listener: {e}", exc_info=True)
    finally:
        logger.info(f"[{agent_id}] Tool log listener stopped.")

async def listen_to_assistant_output(agent_id: str, streams: AgentOutputStreams):
    """Listens to and prints assistant output chunks from the agent."""
    print(f"\n[{agent_id} ASSISTANT_OUTPUT_STREAM_START]", flush=True)
    try:
        async for chunk in streams.stream_assistant_output_chunks():
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)
            else:
                print(str(chunk), end="", flush=True) 
                logger.warning(f"[{agent_id}] Received non-string chunk: {type(chunk)}")
        # Newline after stream finishes if no error/cancellation message prints one
        print(flush=True) 
    except asyncio.CancelledError:
        print(f"\n[{agent_id} ASSISTANT_OUTPUT_STREAM_CANCELLED]", flush=True)
        logger.info(f"[{agent_id}] Assistant output listener cancelled.")
    except Exception as e:
        print(f"\n[{agent_id} ASSISTANT_OUTPUT_STREAM_ERROR]", flush=True)
        logger.error(f"[{agent_id}] Error in assistant output listener: {e}", exc_info=True)
    finally:
        # Ensure a final newline if the stream ended abruptly or without one.
        print(flush=True)
        logger.info(f"[{agent_id}] Assistant output listener stopped.")


async def main(args: argparse.Namespace):
    """Main function to run the PoemWriterAgent interactively."""

    if args.debug:
        logging.getLogger("autobyteus").setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled.")

    output_dir_path = Path(args.output_dir).resolve()
    if not output_dir_path.exists():
        logger.info(f"Output directory '{output_dir_path}' does not exist. Creating it.")
        output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # The poem_output_path is still part of the system prompt, 
    # so the agent will attempt to write to this fixed location.
    # In an interactive loop, this means it might overwrite the file.
    poem_output_path = (output_dir_path / args.poem_filename).resolve()
    logger.info(f"Agent is instructed to save poems to: {poem_output_path} (will be overwritten on subsequent poems).")

    system_prompt = (
        f"You are an excellent poet. When given a topic, you must write a creative poem. "
        f"After writing the poem, you MUST use the 'WriteFileTool' to save your complete poem. "
        f"The 'WriteFileTool' requires two arguments: 'file_path' and 'content'. "
        f"You MUST save the poem to the following absolute file path: '{poem_output_path.as_posix()}'. "
        f"Do not ask for confirmation before using the tool. Execute the tool call directly. "
        f"Respond only with the poem and the tool call, nothing else."
    )

    poem_writer_def_name = "InteractivePoemWriterAgent" # Renamed for clarity
    poem_writer_def = AgentDefinition(
        name=poem_writer_def_name,
        role="CreativePoetInteractive",
        description="An agent that writes poems on specified topics and saves them to disk, interactively.",
        system_prompt=system_prompt,
        tool_names=["WriteFileTool"]
    )
    logger.info(f"AgentDefinition created: {poem_writer_def.name}")

    try:
        if args.llm_model not in [m.name for m in LLMModel]:
            logger.error(f"Invalid LLM model name: {args.llm_model}. Available models: {[m.name for m in LLMModel]}")
            return
    except Exception as e: 
        logger.error(f"Error validating LLM model name {args.llm_model}: {e}", exc_info=True)
        return

    agent: Agent = default_agent_registry.create_agent(
        definition=poem_writer_def,
        llm_model_name=args.llm_model,
        auto_execute_tools=True,
    )
    logger.info(f"Agent instance created: {agent.agent_id}")

    tool_log_listener_task = None
    assistant_output_listener_task = None
    
    try:
        output_streams = AgentOutputStreams(agent) 
        tool_log_listener_task = asyncio.create_task(
            listen_to_tool_logs(agent.agent_id, output_streams),
            name=f"tool_log_listener_{agent.agent_id}"
        )
        assistant_output_listener_task = asyncio.create_task(
            listen_to_assistant_output(agent.agent_id, output_streams),
            name=f"assistant_output_listener_{agent.agent_id}"
        )

        agent.start()
        logger.info(f"Agent {agent.agent_id} starting... Type '/quit' or '/exit' to stop.")
        
        # Brief pause to let agent fully start and listeners to attach if there are startup messages.
        await asyncio.sleep(0.2) 

        # Handle initial topic if provided
        if args.topic:
            logger.info(f"Processing initial topic: '{args.topic}'")
            initial_message = AgentInputUserMessage(content=args.topic)
            print(f"You (initial topic): {args.topic}", flush=True) # Echo the initial topic
            await agent.post_user_message(initial_message)
            # Wait for a short while to let the agent process the initial topic
            # This is a simple way to let one interaction play out before prompting again
            await asyncio.sleep(args.initial_topic_wait_time) 


        # Interactive loop
        while True:
            try:
                # Use asyncio.to_thread to run input() in a separate thread
                user_input_text = await asyncio.to_thread(input, "You: ")
            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e):
                    # Fallback for environments where to_thread might have issues (e.g. older Python in some setups)
                    # This is less ideal as it uses the default executor.
                    loop = asyncio.get_running_loop()
                    user_input_text = await loop.run_in_executor(None, input, "You: ")
                else:
                    raise

            if user_input_text.lower() in ["/quit", "/exit"]:
                logger.info("Exit command received. Shutting down...")
                break
            if not user_input_text.strip():
                continue

            message = AgentInputUserMessage(content=user_input_text)
            await agent.post_user_message(message)
            # No explicit wait here, streams will show output as it comes.

        logger.info("Interactive loop ended.")

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")
    except Exception as e:
        logger.error(f"An error occurred during the script execution: {e}", exc_info=True)
    finally:
        logger.info("Initiating shutdown sequence...")
        listener_tasks_to_cancel = []
        if tool_log_listener_task and not tool_log_listener_task.done():
            logger.debug("Cancelling tool log listener task...")
            tool_log_listener_task.cancel()
            listener_tasks_to_cancel.append(tool_log_listener_task)
        
        if assistant_output_listener_task and not assistant_output_listener_task.done():
            logger.debug("Cancelling assistant output listener task...")
            assistant_output_listener_task.cancel()
            listener_tasks_to_cancel.append(assistant_output_listener_task)

        if listener_tasks_to_cancel:
            logger.debug(f"Waiting for {len(listener_tasks_to_cancel)} listener tasks to cancel...")
            results = await asyncio.gather(*listener_tasks_to_cancel, return_exceptions=True)
            for i, result in enumerate(results):
                task_name = listener_tasks_to_cancel[i].get_name() # Tasks were named at creation
                if isinstance(result, asyncio.CancelledError):
                    logger.info(f"Listener task '{task_name}' successfully cancelled.")
                elif isinstance(result, Exception):
                    logger.error(f"Error during cancellation/shutdown of listener task '{task_name}': {result}", exc_info=result)
                else:
                    logger.info(f"Listener task '{task_name}' completed.")
        
        if 'agent' in locals() and agent and agent.is_running:
            logger.info(f"Stopping agent {agent.agent_id}...")
            await agent.stop(timeout=20)
            logger.info(f"Agent {agent.agent_id} stopped. Final status: {agent.get_status()}")
        elif 'agent' in locals() and agent:
             logger.info(f"Agent {agent.agent_id} was not running or already stopped. Final status: {agent.get_status()}")
        else:
            logger.info("Agent was not running or instance not available.")
        
        if args.output_dir_is_temporary and output_dir_path.exists():
             try:
                 if poem_output_path.exists():
                     poem_output_path.unlink()
                 if not any(output_dir_path.iterdir()):
                     output_dir_path.rmdir()
                     logger.info(f"Temporary output directory '{output_dir_path}' and its contents cleaned up.")
                 else:
                     logger.info(f"Temporary output directory '{output_dir_path}' was not empty, not removed. Contains other files.")
             except Exception as e_cleanup:
                 logger.warning(f"Error during temporary directory cleanup: {e_cleanup}")

    logger.info("Poem writer script finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PoemWriterAgent interactively to generate and save poems.")
    parser.add_argument(
        "--topic",
        type=str,
        default=None, # Made optional for interactive mode
        help="Optional: The initial topic for the first poem."
    )
    parser.add_argument(
        "--initial-topic-wait-time",
        type=float,
        default=5.0,
        help="Time in seconds to wait after processing an initial topic before prompting for new input."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None, 
        help="Directory to save the poem(s). Defaults to a temporary directory."
    )
    parser.add_argument(
        "--poem-filename",
        type=str,
        default="poem_interactive.txt", # Changed default filename
        help="Filename for the saved poem. Will be overwritten for each new poem."
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="GPT_4O_API", 
        help=f"The LLM model to use (e.g., {', '.join([m.name for m in LLMModel])})."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for autobyteus components and this script."
    )

    parsed_args = parser.parse_args()

    temp_dir_obj = None
    if parsed_args.output_dir is None:
        try:
            temp_dir_obj = tempfile.TemporaryDirectory(prefix="poem_writer_interactive_") # Changed prefix
            parsed_args.output_dir = temp_dir_obj.name
            parsed_args.output_dir_is_temporary = True 
            logger.info(f"Using temporary directory for output: {parsed_args.output_dir}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory: {e}. Please specify --output-dir.", exc_info=True)
            sys.exit(1)
    else:
        parsed_args.output_dir_is_temporary = False

    try:
        asyncio.run(main(parsed_args))
    except KeyboardInterrupt: # This handles Ctrl+C at the asyncio.run level if not caught earlier
        logger.info("Script interrupted by user (KeyboardInterrupt at top level). Shutting down...")
    except Exception as e_global:
        logger.error(f"Unhandled global exception in script: {e_global}", exc_info=True)
    finally:
        if temp_dir_obj:
            try:
                temp_dir_obj.cleanup()
                logger.info(f"Successfully cleaned up temporary directory: {temp_dir_obj.name}")
            except Exception as e_temp_cleanup:
                logger.warning(f"Could not cleanup temporary directory {temp_dir_obj.name}: {e_temp_cleanup}")
        logger.info("Exiting script.")

