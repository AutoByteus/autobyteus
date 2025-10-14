# file: autobyteus/examples/run_agentic_software_engineer.py
import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os

# --- Boilerplate to make the script runnable from the project root ---
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables from .env file in the project root
try:
    from dotenv import load_dotenv
    env_file_path = PACKAGE_ROOT / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path)
        print(f"Loaded environment variables from: {env_file_path}")
    else:
        print(f"Info: No .env file found at: {env_file_path}. Relying on exported environment variables.")
except ImportError:
    print("Warning: python-dotenv not installed. Cannot load .env file.")

# --- Imports for the Agentic Software Engineer Example ---
try:
    # Tool related imports
    from autobyteus.tools.registry import default_tool_registry
    from autobyteus.tools.tool_origin import ToolOrigin
    # Import local tools to ensure they are registered
    import autobyteus.tools.local_tools

    # Workspace imports
    from autobyteus.agent.workspace.local_workspace import LocalWorkspace
    from autobyteus.agent.workspace.workspace_config import WorkspaceConfig

    # For Agent creation
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent.factory.agent_factory import AgentFactory
    from autobyteus.cli import agent_cli
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
logger = logging.getLogger("agentic_swe_example")
interactive_logger = logging.getLogger("autobyteus.cli.interactive")

def setup_logging(args: argparse.Namespace):
    """
    Configures logging for the interactive session.
    """
    loggers_to_clear = [
        logging.getLogger(),
        logging.getLogger("autobyteus"),
        logging.getLogger("autobyteus.cli"),
        interactive_logger,
    ]
    for l in loggers_to_clear:
        if l.hasHandlers():
            for handler in l.handlers[:]:
                l.removeHandler(handler)
                if hasattr(handler, 'close'): handler.close()

    script_log_level = logging.DEBUG if args.debug else logging.INFO

    # 1. Handler for unformatted interactive output
    interactive_handler = logging.StreamHandler(sys.stdout)
    interactive_logger.addHandler(interactive_handler)
    interactive_logger.setLevel(logging.INFO)
    interactive_logger.propagate = False

    # 2. Handler for formatted console logs
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    class FormattedConsoleFilter(logging.Filter):
        def filter(self, record):
            if record.name.startswith("agentic_swe_example") or record.name.startswith("autobyteus.cli"):
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
    
    # 3. Handler for the main agent log file
    log_file_path = Path(args.agent_log_file).resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    agent_file_handler = logging.FileHandler(log_file_path, mode='w')  
    agent_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    agent_file_handler.setFormatter(agent_file_formatter)
    file_log_level = logging.DEBUG if args.debug else logging.INFO

    autobyteus_logger = logging.getLogger("autobyteus")
    autobyteus_logger.addHandler(agent_file_handler)
    autobyteus_logger.setLevel(file_log_level)
    autobyteus_logger.propagate = True

    # 4. Configure `autobyteus.cli` package logging
    cli_logger = logging.getLogger("autobyteus.cli")
    cli_logger.setLevel(script_log_level)
    cli_logger.propagate = True
    
    logger.info(f"Core library logs (excluding CLI) redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")

# --- Environment Variable Checks ---
def check_required_env_vars():
    """Checks for environment variables required by this example. None are strictly required."""
    logger.info("No specific environment variables are required, but ensure your chosen LLM provider's API key is set (e.g., GOOGLE_API_KEY).")
    return {}

async def main(args: argparse.Namespace):
    """Main function to configure and run the Agentic Software Engineer."""
    logger.info("--- Starting Agentic Software Engineer Example ---")
    check_required_env_vars()

    try:
        # 1. Create a workspace for the agent.
        workspace_path = Path(args.workspace_path).resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Agent workspace initialized at: {workspace_path}")
        workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
        workspace = LocalWorkspace(config=workspace_config)

        # 2. Get all available local tools.
        tool_registry = default_tool_registry
        local_tool_defs = tool_registry.get_tools_by_origin(ToolOrigin.LOCAL)
        local_tool_names = [tool_def.name for tool_def in local_tool_defs]
        
        if not local_tool_names:
            logger.error("No local tools were found in the registry. Cannot create agent.")
            return

        logger.info(f"Creating instances for registered local tools: {local_tool_names}")
        tools_for_agent = [tool_registry.create_tool(name) for name in local_tool_names]
        
        # 3. Configure and create the agent.
        try:
            _ = LLMModel[args.llm_model]
        except (KeyError, ValueError):
            logger.error(f"LLM Model '{args.llm_model}' is not valid or ambiguous.", file=sys.stderr)
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
        
        # Load system prompt from file
        prompt_path = SCRIPT_DIR / "prompts" / "agentic_software_engineer.prompt"
        if not prompt_path.exists():
            logger.error(f"System prompt file not found at: {prompt_path}")
            sys.exit(1)
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        logger.info(f"Loaded system prompt from: {prompt_path}")

        agent_config = AgentConfig(
            name="AgenticSoftwareDeveloper",
            role="SoftwareEngineer",
            description="An AI agent that can reason, plan, and execute software development tasks.",
            llm_instance=llm_instance,
            system_prompt=system_prompt,
            tools=tools_for_agent,
            workspace=workspace,
            use_xml_tool_format=True,  # As specified in the prompt
            auto_execute_tools=False   # Require user approval for safety
        )

        agent = AgentFactory().create_agent(config=agent_config)
        logger.info(f"Agentic Software Engineer instance created: {agent.agent_id}")

        # 4. Run the agent in an interactive CLI session.
        logger.info(f"Starting interactive session for agent {agent.agent_id}...")
        initial_prompt = f"Hello! I'm ready to work. My current working directory is `{workspace_path}`. What's the first task?"
        await agent_cli.run(agent=agent, initial_prompt=initial_prompt, show_tool_logs=not args.no_tool_logs)
        logger.info(f"Interactive session for agent {agent.agent_id} finished.")

    except Exception as e:
        logger.error(f"An error occurred during the agent workflow: {e}", exc_info=True)
    
    logger.info("--- Agentic Software Engineer Example Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Agentic Software Engineer interactively.")
    parser.add_argument("--llm-model", type=str, default="gemini-2.0-flash-", help=f"The LLM model identifier to use. Call --help-models for list.")
    parser.add_argument("--workspace-path", type=str, default="./agent_workspace", help="Path to the agent's working directory. (Default: ./agent_workspace)")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs_swe.txt", 
                       help="Path to the log file for autobyteus.* library logs. (Default: ./agent_logs_swe.txt)")
    parser.add_argument("--no-tool-logs", action="store_true", 
                        help="Disable display of [Tool Log (...)] messages on the console by the agent_cli.")

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
    check_required_env_vars()

    try:
        asyncio.run(main(parsed_args))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"An unhandled error occurred at the top level: {e}", exc_info=True)
    finally:
        logger.info("Exiting script.")
