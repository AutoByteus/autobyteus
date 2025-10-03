# file: autobyteus/examples/run_poem_writer.py
import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os
from typing import Optional

# Ensure the autobyteus package is discoverable
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))

# Also add the server package root to resolve workspace imports
SERVER_PACKAGE_ROOT = PACKAGE_ROOT.parent / "autobyteus-server"
if SERVER_PACKAGE_ROOT.exists() and str(SERVER_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_PACKAGE_ROOT))

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
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent.factory.agent_factory import AgentFactory
    from autobyteus.cli import agent_cli
    from autobyteus.tools.file.file_writer import file_writer
    # Import core workspace and schema components from the library
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
except ImportError as e: # pragma: no cover
    print(f"Error importing autobyteus components: {e}")
    print("Please ensure that the autobyteus and autobyteus-server libraries are installed and accessible in your PYTHONPATH.")
    print(f"Attempted to add to sys.path: {str(PACKAGE_ROOT)} and {str(SERVER_PACKAGE_ROOT)}") 
    sys.exit(1)

# --- Minimal, Self-Contained Workspace for this Example ---
class SimpleLocalWorkspace(BaseAgentWorkspace):
    """A minimal, self-contained workspace for local file system access, for example scripts."""

    def __init__(self, config: WorkspaceConfig):
        super().__init__(config)
        self.root_path: str = config.get("root_path")
        if not self.root_path:
            raise ValueError("SimpleLocalWorkspace requires a 'root_path' in its config.")

    def get_base_path(self) -> str:
        return self.root_path

    @classmethod
    def get_workspace_type_name(cls) -> str:
        return "simple_local_example_workspace"

    @classmethod
    def get_description(cls) -> str:
        return "A basic workspace for local file access within an example script."

    @classmethod
    def get_config_schema(cls) -> ParameterSchema:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="root_path",
            param_type=ParameterType.STRING,
            description="The absolute local file path for the workspace root.",
            required=True
        ))
        return schema

# Logger for this script
logger = logging.getLogger("run_poem_writer")
# Logger for interactive CLI output
interactive_logger = logging.getLogger("autobyteus.cli.interactive")

def setup_logging(args: argparse.Namespace):
    """
    Configure logging for the interactive session.
    """
    # --- Clear existing handlers from all relevant loggers ---
    loggers_to_clear = [
        logging.getLogger(), # Root logger
        logging.getLogger("autobyteus"),
        logging.getLogger("autobyteus-server"),
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
    interactive_logger.addHandler(interactive_handler)
    interactive_logger.setLevel(logging.INFO)
    interactive_logger.propagate = False

    # --- 2. Handler for formatted console logs (script + CLI debug) ---
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    class FormattedConsoleFilter(logging.Filter):
        def filter(self, record):
            if record.name.startswith("run_poem_writer") or record.name.startswith("autobyteus.cli"):
                return True
            if record.levelno >= logging.CRITICAL:
                return True
            return False

    formatted_console_handler = logging.StreamHandler(sys.stdout)
    formatted_console_handler.setFormatter(console_formatter)
    formatted_console_handler.addFilter(FormattedConsoleFilter())
    
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
    autobyteus_logger = logging.getLogger("autobyteus")
    autobyteus_logger.addHandler(agent_file_handler)
    autobyteus_logger.setLevel(file_log_level)
    autobyteus_logger.propagate = True

    # --- 5. Isolate noisy queue manager logs to a separate file in debug mode ---
    if args.debug:
        queue_log_file_path = Path("./queue_logs.txt").resolve()
        
        queue_file_handler = logging.FileHandler(queue_log_file_path, mode='w')
        queue_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        queue_file_handler.setFormatter(queue_file_formatter)
        
        queue_logger = logging.getLogger("autobyteus.agent.events.agent_input_event_queue_manager")
        
        queue_logger.setLevel(logging.DEBUG)
        queue_logger.addHandler(queue_file_handler)
        queue_logger.propagate = False

        logger.info(f"Debug mode: Redirecting noisy queue manager DEBUG logs to: {queue_log_file_path}")

    # --- 6. Configure `autobyteus.cli` package logging ---
    cli_logger = logging.getLogger("autobyteus.cli")
    cli_logger.setLevel(script_log_level)
    cli_logger.propagate = True
    
    logger.info(f"Core library logs (excluding CLI) redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")

async def main(args: argparse.Namespace):
    """Main function to configure and run the PoemWriterAgent."""

    workspace_base_path = Path(args.output_dir).resolve()
    workspace_base_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Agent will be configured with a local workspace at: {workspace_base_path}")

    # The file_writer tool is an instance ready to be used
    tools_for_agent = [file_writer]
    
    # UPDATED: The system prompt now provides context about the workspace.
    system_prompt = (
        f"You are a world-class poet working inside a dedicated file workspace. Your task is to write a creative and beautiful poem on the given topic.\n"
        f"After composing the poem, you MUST use the available tool to save your work. Because you are in a workspace, you only need to provide a relative path; simply use the filename '{args.poem_filename}'.\n"
        f"Conclude your response with only the tool call necessary to save the poem.\n\n"
        f"Here is the manifest of tools available to you, including their definitions and examples:\n"
        f"{{{{tools}}}}"
    )

    try:
        # Validate the LLM model name
        _ = LLMModel[args.llm_model]
    except (ValueError, KeyError):
        logger.error(f"LLM Model '{args.llm_model}' is not valid or is ambiguous.", file=sys.stderr)
        try:
            LLMFactory.ensure_initialized()
            print("\nAvailable LLM Models (use the 'Identifier' with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - Display Name: {model.name:<30} Identifier: {model.model_identifier}")
        except Exception as e:
            print(f"Additionally, an error occurred while listing models: {e}", file=sys.stderr)
        sys.exit(1)

    logger.info(f"Creating LLM instance for model: {args.llm_model}")
    llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

    # --- Create and configure the workspace using the self-contained class ---
    logger.info(f"Configuring SimpleLocalWorkspace with root path: {str(workspace_base_path)}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_base_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    # Create the single, unified AgentConfig object
    poem_writer_config = AgentConfig(
        name="PoemWriterAgent",
        role="CreativePoet",
        description="An agent that writes poems and saves them to disk.",
        llm_instance=llm_instance,
        system_prompt=system_prompt,
        tools=tools_for_agent,
        workspace=workspace,
        auto_execute_tools=False
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
    parser.add_argument("--output-dir", type=str, default="./poem_writer_output", help="Directory to save the poem(s). Defaults to './poem_writer_output'.")
    parser.add_argument("--poem-filename", type=str, default="poem_interactive.txt", help="Filename for the saved poem.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o", help=f"The LLM model identifier to use. Call --help-models for list.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging. This will create detailed agent_logs.txt and a separate queue_logs.txt for noisy logs.")
    parser.add_argument("--no-tool-logs", action="store_true", 
                        help="Disable display of [Tool Log (...)] messages on the console by the agent_cli.")
    
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs.txt", 
                       help="Path to the log file for autobyteus.* library logs. (Default: ./agent_logs.txt)")
    
    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized() 
            print("Available LLM Models (use the 'Identifier' with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - Display Name: {model.name:<30} Identifier: {model.model_identifier}")
        except Exception as e:
            print(f"Error listing models: {e}")
        sys.exit(0)

    parsed_args = parser.parse_args()
    
    setup_logging(parsed_args) 

    try:
        asyncio.run(main(parsed_args))
    except KeyboardInterrupt: 
        logger.info("Script interrupted by user (KeyboardInterrupt at top level).")
    except Exception as e_global:
        logger.error(f"Unhandled global exception in script: {e_global}", exc_info=True)
    finally:
        logger.info("Exiting script.")
