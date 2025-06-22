# file: autobyteus/examples/run_poem_writer.py
import asyncio
import logging
import argparse
from pathlib import Path
import tempfile
import sys
import os

# Ensure the autobyteus package is discoverable
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables from .env file in the project root
try:
    from dotenv import load_dotenv
    env_file_path = PACKAGE_ROOT / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path)
        print(f"Loaded environment variables from: {env_file_path}")
    else:
        print(f"No .env file found at: {env_file_path}")
except ImportError: # pragma: no cover
    print("Warning: python-dotenv not installed. Environment variables from .env file will not be loaded.")
    print("Install with: pip install python-dotenv")
except Exception as e: # pragma: no cover
    print(f"Error loading .env file: {e}")

try:
    # Import autobyteus components from the current implementation
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory
    from autobyteus.agent.factory.agent_factory import AgentFactory
    from autobyteus.cli import agent_cli
    from autobyteus.tools.file.file_writer import file_writer
except ImportError as e: # pragma: no cover
    print(f"Error importing autobyteus components: {e}")
    print("Please ensure that the autobyteus library is installed and accessible in your PYTHONPATH.")
    print(f"Attempted to add to sys.path: {str(PACKAGE_ROOT)}") 
    sys.exit(1)

# Logger for this script
logger = logging.getLogger("run_poem_writer")
# Logger for interactive CLI output
interactive_logger = logging.getLogger("autobyteus.cli.interactive")

def setup_logging(args: argparse.Namespace):
    """
    Configure logging for the interactive session.
    - 1. A dedicated "interactive" logger ("autobyteus.cli.interactive") handles unformatted conversational output.
    - 2. A standard console logger handles formatted logs from this script and the `autobyteus.cli` package.
    - 3. A file handler sends most library logs (e.g., from `autobyteus.agent`) to `agent_logs.txt`.
    - 4. In debug mode, very noisy logs (from the event queue manager) are automatically redirected to `queue_logs.txt`.
    """
    # --- Clear existing handlers from all relevant loggers ---
    loggers_to_clear = [
        logging.getLogger(), # Root logger
        logging.getLogger("autobyteus"),
        logging.getLogger("autobyteus.cli"),
        logging.getLogger("autobyteus.cli.interactive"),
    ]
    for l in loggers_to_clear:
        if l.hasHandlers():
            for handler in l.handlers[:]:
                l.removeHandler(handler)
                if hasattr(handler, 'close'): handler.close()

    script_log_level = logging.DEBUG if args.debug else logging.INFO

    # --- 1. Handler for unformatted interactive output (replicates print) ---
    interactive_handler = logging.StreamHandler(sys.stdout)
    # NO formatter, so it just prints the message as-is.
    interactive_logger.addHandler(interactive_handler)
    interactive_logger.setLevel(logging.INFO)
    interactive_logger.propagate = False # Crucial: Don't let it bubble up to be formatted again.

    # --- 2. Handler for formatted console logs (script + CLI debug) ---
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    class FormattedConsoleFilter(logging.Filter):
        def filter(self, record):
            # Allow messages from this script or from the entire `autobyteus.cli` package.
            if record.name.startswith("run_poem_writer") or record.name.startswith("autobyteus.cli"):
                return True
            if record.levelno >= logging.CRITICAL: # Always show critical errors
                return True
            return False

    formatted_console_handler = logging.StreamHandler(sys.stdout)
    formatted_console_handler.setFormatter(console_formatter)
    formatted_console_handler.addFilter(FormattedConsoleFilter())
    
    # Attach this handler to the root logger.
    root_logger = logging.getLogger()
    root_logger.addHandler(formatted_console_handler)
    root_logger.setLevel(script_log_level) 
    
    # --- 3. Handler for the main agent log file ---
    log_file_path = Path(args.agent_log_file).resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    agent_file_handler = logging.FileHandler(log_file_path, mode='w')  
    agent_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    agent_file_handler.setFormatter(agent_file_formatter)
    file_log_level = logging.DEBUG if args.debug else logging.INFO

    # --- 4. Configure `autobyteus` package logging ---
    # Attach the file handler to the top-level `autobyteus` logger.
    autobyteus_logger = logging.getLogger("autobyteus")
    autobyteus_logger.addHandler(agent_file_handler)
    autobyteus_logger.setLevel(file_log_level)
    autobyteus_logger.propagate = True # Allow propagation up to root.

    # --- 5. Isolate noisy queue manager logs to a separate file in debug mode ---
    if args.debug:
        queue_log_file_path = Path("./queue_logs.txt").resolve()
        
        # Handler for the queue logs
        queue_file_handler = logging.FileHandler(queue_log_file_path, mode='w')
        # Use a simpler format for these high-volume logs
        queue_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        queue_file_handler.setFormatter(queue_file_formatter)
        
        # Get the specific logger to isolate
        queue_logger = logging.getLogger("autobyteus.agent.events.agent_input_event_queue_manager")
        
        # Configure it
        queue_logger.setLevel(logging.DEBUG)
        queue_logger.addHandler(queue_file_handler)
        queue_logger.propagate = False # IMPORTANT: Stop logs from bubbling up to the main agent_logs.txt

        logger.info(f"Debug mode: Redirecting noisy queue manager DEBUG logs to: {queue_log_file_path}")

    # --- 6. Configure `autobyteus.cli` package logging ---
    # Specifically configure the `autobyteus.cli` logger.
    # We want it to use the root's console handler, NOT the file handler.
    cli_logger = logging.getLogger("autobyteus.cli")
    cli_logger.setLevel(script_log_level)
    cli_logger.propagate = True # This ensures it goes to the root logger's console handler.
    # By not adding the file handler here, it won't write to the file.
    
    logger.info(f"Core library logs (excluding CLI) redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")

async def main(args: argparse.Namespace):
    """Main function to configure and run the PoemWriterAgent."""

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    poem_output_path = (output_dir / args.poem_filename).resolve()
    
    logger.info(f"Agent will be instructed to save poems to: {poem_output_path}")

    # The file_writer tool is an instance ready to be used
    tools_for_agent = [file_writer]
    
    # UPDATED: The system prompt now only uses the {{tools}} placeholder.
    # The new ToolManifestInjectorProcessor will inject both the schema and an example.
    system_prompt = (
        f"You are a world-class poet. Your task is to write a creative and beautiful poem on the given topic.\n"
        f"After composing the poem, you MUST use the '{file_writer.get_name()}' tool to save your work.\n"
        f"When using the tool, you MUST use the absolute file path '{poem_output_path.as_posix()}' for the 'path' argument.\n"
        f"Conclude your response with only the tool call necessary to save the poem.\n\n"
        f"Here is the manifest of tools available to you, including their definitions and examples:\n"
        f"{{{{tools}}}}"
    )

    try:
        # Validate the LLM model name
        _ = LLMModel[args.llm_model]
    except (ValueError, KeyError):
        logger.error(f"LLM Model '{args.llm_model}' is not valid.")
        logger.info(f"Available models: {[m.value for m in LLMModel]}")
        sys.exit(1)

    # --- User is now responsible for creating the LLM instance ---
    logger.info(f"Creating LLM instance for model: {args.llm_model}")
    # The factory can be used as a convenience, or the user could instantiate their own LLM class directly.
    llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

    # Create the single, unified AgentConfig object
    poem_writer_config = AgentConfig(
        name="PoemWriterAgent",
        role="CreativePoet",
        description="An agent that writes poems and saves them to disk.",
        llm_instance=llm_instance, # Pass the LLM instance directly
        system_prompt=system_prompt,
        tools=tools_for_agent, # Pass the list of tool instances
        auto_execute_tools=False, # We want to approve the file write
        use_xml_tool_format=False
    )

    # Use the AgentFactory to create the agent
    agent = AgentFactory().create_agent(config=poem_writer_config)
    logger.info(f"Agent instance created: {agent.agent_id}")

    try:
        logger.info(f"Starting interactive session for agent {agent.agent_id} via agent_cli.run()...")
        await agent_cli.run(
            agent=agent
        )
        logger.info(f"Interactive session for agent {agent.agent_id} finished.")
    except KeyboardInterrupt: 
        logger.info("KeyboardInterrupt received during interactive session. agent_cli.run should handle shutdown.")
    except Exception as e: 
        logger.error(f"An error occurred during the agent interaction: {e}", exc_info=True)
    finally:
        logger.info("Poem writer script finished.")


if __name__ == "__main__": # pragma: no cover
    parser = argparse.ArgumentParser(description="Run the PoemWriterAgent interactively to generate and save poems.")
    parser.add_argument("--topic", type=str, default=None, help="Optional: The initial topic for the first poem.")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save the poem(s). Defaults to a temporary directory.")
    parser.add_argument("--poem-filename", type=str, default="poem_interactive.txt", help="Filename for the saved poem.")
    parser.add_argument("--llm-model", type=str, default="GEMINI_2_0_FLASH_API", help=f"The LLM model to use. Call --help-models for list.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging. This will create detailed agent_logs.txt and a separate queue_logs.txt for noisy logs.")
    parser.add_argument("--no-tool-logs", action="store_true", 
                        help="Disable display of [Tool Log (...)] messages on the console by the agent_cli.")
    
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs.txt", 
                       help="Path to the log file for autobyteus.* library logs. (Default: ./agent_logs.txt)")
    
    if "--help-models" in sys.argv:
        try:
            from autobyteus.llm.llm_factory import LLMFactory 
            LLMFactory.ensure_initialized() 
            print("Available LLM Models:")
            model_names = [m.name for m in LLMModel] if LLMModel else []
            for model_name in sorted(model_names): print(f"  - {model_name}")
        except ImportError as e_llm: print(f"Could not import LLM components to list models: {e_llm}")
        except Exception as e_llm_init: print(f"Error initializing LLM components to list models: {e_llm_init}")
        sys.exit(0)

    parsed_args = parser.parse_args()
    
    setup_logging(parsed_args) 
    
    temp_dir_obj = None 
    if parsed_args.output_dir is None:
        try:
            temp_dir_obj = tempfile.TemporaryDirectory(prefix="poem_writer_interactive_") 
            parsed_args.output_dir = temp_dir_obj.name
            logger.info(f"Using temporary directory for output: {parsed_args.output_dir}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory: {e}. Please specify --output-dir.", exc_info=True)
            sys.exit(1)

    try:
        asyncio.run(main(parsed_args))
    except KeyboardInterrupt: 
        logger.info("Script interrupted by user (KeyboardInterrupt at top level).")
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
