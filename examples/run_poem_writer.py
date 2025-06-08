import asyncio
import logging
import argparse
from pathlib import Path
import tempfile
import sys
import os

# Ensure the autobyteus package is discoverable if running script from examples dir directly
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
    from autobyteus.agent.registry.agent_definition import AgentDefinition
    from autobyteus.llm.models import LLMModel
    from autobyteus.agent.registry.agent_registry import default_agent_registry
    from autobyteus.agent.agent import Agent
    from autobyteus.cli import agent_cli

    from autobyteus.tools import file_writer # Assuming file_writer module contains FileWriterTool

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
    - A dedicated "interactive" logger ("autobyteus.cli.interactive") handles unformatted conversational output.
    - A standard console logger handles formatted logs from this script and the entire `autobyteus.cli` package.
    - All other library logs (e.g., `autobyteus.agent`, `autobyteus.llm`) go to the specified file.
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

    # Specifically configure the `autobyteus.cli` logger.
    # We want it to use the root's console handler, NOT the file handler.
    cli_logger = logging.getLogger("autobyteus.cli")
    cli_logger.setLevel(script_log_level)
    cli_logger.propagate = True # This ensures it goes to the root logger's console handler.
    # By not adding the file handler here, it won't write to the file.
    
    logger.info(f"Core library logs (excluding CLI) redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")
    logger.info(f"Console output is for this script's messages, CLI debug info, and interactive chat.")


async def main(args: argparse.Namespace): # pragma: no cover
    """Main function to run the PoemWriterAgent interactively using agent_cli.run()."""

    output_dir_path = Path(args.output_dir).resolve()
    if not output_dir_path.exists():
        logger.info(f"Output directory '{output_dir_path}' does not exist. Creating it.")
        output_dir_path.mkdir(parents=True, exist_ok=True)
    
    poem_output_path = (output_dir_path / args.poem_filename).resolve()
    logger.info(f"Agent is instructed to save poems to: {poem_output_path} (will be overwritten on subsequent poems).")
    
    # Simplified tool name retrieval
    tool_class_name = file_writer.get_name()

    system_prompt = (
        f"You are an excellent poet. When given a topic, you must write a creative poem.\n"
        f"After writing the poem, you MUST use the '{tool_class_name}' tool to save your complete poem.\n"
        f"When using the '{tool_class_name}', you MUST use the absolute file path '{poem_output_path.as_posix()}' for its 'path' argument.\n"
        f"Respond only with a tool call, nothing else.\n\n"
        f"You have access to the following tools:\n"
        f"{{{{tools}}}}\n\n" 
        f"{{{{tool_examples}}}}" 
    )

    poem_writer_def_name = "InteractivePoemWriterAgent"
    poem_writer_def = AgentDefinition(
        name=poem_writer_def_name,
        role="CreativePoetInteractive",
        description="An agent that writes poems on specified topics and saves them to disk, interactively.",
        system_prompt=system_prompt,
        tool_names=[tool_class_name] 
    )
    logger.info(f"AgentDefinition created: {poem_writer_def.name} using tool name '{tool_class_name}'")

    try:
        _ = LLMModel[args.llm_model]
    except KeyError:
        logger.error(f"LLM Model '{args.llm_model}' not found in autobyteus.llm.models.LLMModel enum.")
        logger.info(f"Available models: {[m.name for m in LLMModel]}")
        sys.exit(1)

    agent: Agent = default_agent_registry.create_agent(
        definition=poem_writer_def,
        llm_model_name=args.llm_model, 
        auto_execute_tools=False,
    )
    logger.info(f"Agent instance created: {agent.agent_id}")
    
    try:
        logger.info(f"Starting interactive session for agent {agent.agent_id} via agent_cli.run()...")
        await agent_cli.run(
            agent=agent,
            show_tool_logs=not args.no_tool_logs, 
            initial_prompt=args.topic
        )
        logger.info(f"Interactive session for agent {agent.agent_id} finished.")

    except KeyboardInterrupt: 
        logger.info("KeyboardInterrupt received during interactive session. agent_cli.run should handle shutdown.")
    except Exception as e: 
        logger.error(f"An error occurred during the agent interaction: {e}", exc_info=True)
    finally: 
        logger.info("Poem writer script specific cleanup...")
        if hasattr(args, 'output_dir_is_temporary') and args.output_dir_is_temporary:
            if output_dir_path.exists():
                 try:
                     if poem_output_path.exists(): 
                         poem_output_path.unlink()
                     if not any(output_dir_path.iterdir()): 
                         output_dir_path.rmdir()
                         logger.info(f"Temporary output directory '{output_dir_path}' and its contents cleaned up.")
                     else:
                         logger.info(f"Temporary output directory '{output_dir_path}' was not empty. Poem file removed if existed, directory kept.")
                 except Exception as e_cleanup:
                     logger.warning(f"Error during temporary directory cleanup: {e_cleanup}")

    logger.info("Poem writer script finished.")

if __name__ == "__main__": # pragma: no cover
    parser = argparse.ArgumentParser(description="Run the PoemWriterAgent interactively to generate and save poems.")
    parser.add_argument("--topic", type=str, default=None, help="Optional: The initial topic for the first poem.")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save the poem(s). Defaults to a temporary directory.")
    parser.add_argument("--poem-filename", type=str, default="poem_interactive.txt", help="Filename for the saved poem.")
    parser.add_argument("--llm-model", type=str, default="GPT_4o_API", help=f"The LLM model to use. Call --help-models for list.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging for script and library file logs. Isolates noisy queue logs to queue_logs.txt.")
    parser.add_argument("--no-tool-logs", action="store_true", 
                        help="Disable display of [Tool Log (...)] messages on the console by the agent_cli.")
    
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs.txt", 
                       help="Path to the log file for autobyteus.* and httpx logs. (Default: ./agent_logs.txt)")
    
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
            _temp_dir_manager = tempfile.TemporaryDirectory(prefix="poem_writer_interactive_") 
            parsed_args.output_dir = _temp_dir_manager.name
            parsed_args.output_dir_is_temporary = True 
            temp_dir_obj = _temp_dir_manager 
            logger.info(f"Using temporary directory for output: {parsed_args.output_dir}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory: {e}. Please specify --output-dir.", exc_info=True)
            sys.exit(1)
    else:
        parsed_args.output_dir_is_temporary = False

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
