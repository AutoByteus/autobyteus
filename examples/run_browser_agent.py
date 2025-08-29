# file: autobyteus/examples/run_browser_agent.py
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

# --- Imports for the Browser Agent Example ---
try:
    # For MCP Tool Integration
    from autobyteus.tools.mcp import McpToolRegistrar
    from autobyteus.tools.registry import default_tool_registry

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
logger = logging.getLogger("browser_agent_example")
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
            if record.name.startswith("browser_agent_example") or record.name.startswith("autobyteus.cli"):
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

    # 4. Isolate noisy queue manager logs to a separate file in debug mode
    if args.debug:
        queue_log_file_path = Path(log_file_path.parent / f"{log_file_path.stem}_queue.log").resolve()
        
        queue_file_handler = logging.FileHandler(queue_log_file_path, mode='w')
        queue_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        queue_file_handler.setFormatter(queue_file_formatter)
        
        queue_logger = logging.getLogger("autobyteus.agent.events.agent_input_event_queue_manager")
        
        queue_logger.setLevel(logging.DEBUG)
        queue_logger.addHandler(queue_file_handler)
        queue_logger.propagate = False # IMPORTANT: Stop logs from bubbling up to the main agent_logs.txt

        logger.info(f"Debug mode: Redirecting noisy queue manager DEBUG logs to: {queue_log_file_path}")

    # 5. Configure `autobyteus.cli` package logging
    cli_logger = logging.getLogger("autobyteus.cli")
    cli_logger.setLevel(script_log_level)
    cli_logger.propagate = True
    
    logger.info(f"Core library logs (excluding CLI) redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")

# --- Environment Variable Checks ---
def check_required_env_vars():
    """Checks for environment variables required by this example. None are required for the browser agent."""
    # The browser MCP server is self-contained via npx and doesn't require env vars.
    # This function is kept for structural consistency.
    logger.info("No specific environment variables are required for the browser agent example.")
    return {}

async def main(args: argparse.Namespace):
    """Main function to configure and run the BrowserAgent."""
    logger.info("--- Starting Browser Agent Example ---")
    check_required_env_vars()

    # 1. Instantiate the core MCP and registry components.
    tool_registry = default_tool_registry
    registrar = McpToolRegistrar()

    # 2. Define the configuration for the MCP server as a dictionary.
    server_id = "browsermcp"
    browser_mcp_config_dict = {
        server_id: {
            "transport_type": "stdio",
            "stdio_params": {
                "command": "npx",
                "args": ["@browsermcp/mcp@latest"],
                "env": {},
            },
            "enabled": True,
        }
    }

    try:
        # 3. Discover and register tools by passing the config dictionary directly.
        logger.info(f"Performing targeted discovery for remote Browser tools from server: '{server_id}'...")
        await registrar.discover_and_register_tools(mcp_config=browser_mcp_config_dict)
        logger.info("Remote tool registration complete.")

        # 4. Create tool instances from the registry for our agent.
        # Use the ToolRegistry to get tools by their source server ID.
        browser_tool_defs = tool_registry.get_tools_by_mcp_server(server_id)
        browser_tool_names = [tool_def.name for tool_def in browser_tool_defs]

        if not browser_tool_names:
            logger.error(f"No Browser tools were found in the registry for server '{server_id}' after discovery. Cannot create agent.")
            return

        logger.info(f"Creating instances for registered Browser tools: {browser_tool_names}")
        tools_for_agent = [tool_registry.create_tool(name) for name in browser_tool_names]
        
        # 5. Configure and create the agent.
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

        system_prompt = (
            "You are a helpful assistant that can browse the web to find information. "
            "You have access to a set of specialized tools for this purpose.\n"
            "When asked to perform a task on a browser, you should understand the user's intent and use the available tools to fulfill it.\n\n"
            "Here is the manifest of tools available to you, including their definitions and examples:\n"
            "{{tools}}"
        )

        browser_agent_config = AgentConfig(
            name="BrowserAgent",
            role="WebNavigator",
            description="An agent that can browse the web using a set of remote tools.",
            llm_instance=llm_instance,
            system_prompt=system_prompt,
            tools=tools_for_agent,
            auto_execute_tools=False
        )

        agent = AgentFactory().create_agent(config=browser_agent_config)
        logger.info(f"Browser Agent instance created: {agent.agent_id}")

        # 6. Run the agent in an interactive CLI session.
        logger.info(f"Starting interactive session for agent {agent.agent_id}...")
        await agent_cli.run(agent=agent)
        logger.info(f"Interactive session for agent {agent.agent_id} finished.")

    except Exception as e:
        logger.error(f"An error occurred during the agent workflow: {e}", exc_info=True)
    
    logger.info("--- Browser Agent Example Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the BrowserAgent interactively.")
    parser.add_argument("--llm-model", type=str, default="gemini-2.0-flash-", help=f"The LLM model identifier to use. Call --help-models for list.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs_browser.txt", 
                       help="Path to the log file for autobyteus.* library logs. (Default: ./agent_logs_browser.txt)")
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
