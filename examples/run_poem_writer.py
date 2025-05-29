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
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file will not be loaded.")
    print("Install with: pip install python-dotenv")
except Exception as e:
    print(f"Error loading .env file: {e}")

try:
    from autobyteus.agent.registry.agent_definition import AgentDefinition
    from autobyteus.llm.models import LLMModel
    from autobyteus.agent.registry.agent_registry import default_agent_registry
    from autobyteus.agent.agent import Agent
    from autobyteus.cli import agent_cli

    from autobyteus.tools import file_writer

except ImportError as e:
    print(f"Error importing autobyteus components: {e}")
    print("Please ensure that the autobyteus library is installed and accessible in your PYTHONPATH.")
    print(f"Attempted to add to sys.path: {str(PACKAGE_ROOT.parent)}")
    sys.exit(1)

# Logger for this script
logger = logging.getLogger("run_poem_writer")

def setup_logging(args: argparse.Namespace):
    """
    Configure logging. By default for this script, it sends specified
    module logs (autobyteus.*, httpx) to a file to keep the console clean
    for interactive use.
    """
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(console_handler)
    
    if args.debug:
        root_logger.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled for root and run_poem_writer script.")
    else:
        root_logger.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    # For this example script, we will always enable file logging for agent modules
    # to ensure a clean interactive console experience.
    log_file_path = Path(args.agent_log_file).resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    agent_file_handler = logging.FileHandler(log_file_path, mode='w')  
    agent_file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'
    )
    agent_file_handler.setFormatter(agent_file_formatter)
    
    loggers_to_redirect = [
        "autobyteus.agent",
        "autobyteus.llm",
        "autobyteus.tools",
        "autobyteus.cli", 
        "httpx"          
    ]
    
    for logger_name in loggers_to_redirect:
        mod_logger = logging.getLogger(logger_name)
        if mod_logger.hasHandlers():
            mod_logger.handlers.clear()

        mod_logger.addHandler(agent_file_handler)
        mod_logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
        mod_logger.propagate = False 
    
    logger.info(f"Specified module logs (including autobyteus.* and httpx) will be written to: {log_file_path}")
    logger.info("Console output is configured for primarily the agent's direct interaction stream.")


async def main(args: argparse.Namespace):
    """Main function to run the PoemWriterAgent interactively using agent_cli.run()."""

    output_dir_path = Path(args.output_dir).resolve()
    if not output_dir_path.exists():
        logger.info(f"Output directory '{output_dir_path}' does not exist. Creating it.")
        output_dir_path.mkdir(parents=True, exist_ok=True)
    
    poem_output_path = (output_dir_path / args.poem_filename).resolve()
    logger.info(f"Agent is instructed to save poems to: {poem_output_path} (will be overwritten on subsequent poems).")
    
    system_prompt = (
        f"You are an excellent poet. When given a topic, you must write a creative poem.\n"
        f"After writing the poem, you MUST use the '{file_writer.get_name()}' (described in the 'Tools' section below) to save your complete poem.\n"
        f"When using the '{file_writer.get_name()}', you MUST use the absolute file path '{poem_output_path.as_posix()}' for its 'file_path' argument.\n"
        f"Do not ask for confirmation before using the tool. Execute the tool call directly.\n"
        f"Respond only with the poem and the tool call, nothing else.\n\n"
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
        tool_names=[file_writer.get_name()] 
    )
    logger.info(f"AgentDefinition created: {poem_writer_def.name} using tool name '{file_writer.get_name()}'")

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
    
    # Message confirming file logging is now unconditionally part of setup_logging
    # if args.enable_agent_file_logging: # This conditional is no longer needed here
    #    logger.info("Agent module logs are being written to file. Console should now be cleaner for interactive use.")
    
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PoemWriterAgent interactively to generate and save poems.")
    parser.add_argument("--topic", type=str, default=None, help="Optional: The initial topic for the first poem.")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save the poem(s). Defaults to a temporary directory.")
    parser.add_argument("--poem-filename", type=str, default="poem_interactive.txt", help="Filename for the saved poem.")
    parser.add_argument("--llm-model", type=str, default="GPT_4o_API", help=f"The LLM model to use. Call --help-models for list.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging for all configured handlers.")
    parser.add_argument("--no-tool-logs", action="store_true", 
                        help="Disable generation of [TOOL LOG] messages by the agent_cli. "
                             "If file logging is enabled (default), these would normally go to file.")
    
    # REMOVED: --disable-agent-file-logging flag
    
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
    
    # By default, file logging for agent modules is now always enabled for this script.
    # The setup_logging function will use args.agent_log_file and args.debug.
    
    setup_logging(parsed_args) # Call setup_logging early
    
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
            try: temp_dir_obj.cleanup(); logger.info(f"Successfully cleaned up temporary directory: {temp_dir_obj.name}")
            except Exception as e_temp_cleanup: logger.warning(f"Could not cleanup temporary directory {temp_dir_obj.name}: {e_temp_cleanup}")
        logger.info("Exiting script.")

