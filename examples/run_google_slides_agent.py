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

# --- Imports for the Google Slides Agent Example ---
try:
    # For MCP Tool Integration
    from autobyteus.tools.mcp import (
        McpConfigService,
        McpConnectionManager,
        McpSchemaMapper,
        McpToolRegistrar,
    )
    from autobyteus.tools.registry import default_tool_registry

    # For Agent creation
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent.factory.agent_factory import default_agent_factory
    from autobyteus.cli import agent_cli
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
logger = logging.getLogger("google_slides_agent_example")
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

    interactive_handler = logging.StreamHandler(sys.stdout)
    interactive_logger.addHandler(interactive_handler)
    interactive_logger.setLevel(logging.INFO)
    interactive_logger.propagate = False

    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    class FormattedConsoleFilter(logging.Filter):
        def filter(self, record):
            if record.name.startswith("google_slides_agent_example") or record.name.startswith("autobyteus.cli"):
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
    
    log_file_path = Path("./agent_logs_gslides.txt").resolve()
    agent_file_handler = logging.FileHandler(log_file_path, mode='w')  
    agent_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    agent_file_handler.setFormatter(agent_file_formatter)
    file_log_level = logging.DEBUG if args.debug else logging.INFO

    autobyteus_logger = logging.getLogger("autobyteus")
    autobyteus_logger.addHandler(agent_file_handler)
    autobyteus_logger.setLevel(file_log_level)
    autobyteus_logger.propagate = True

    cli_logger = logging.getLogger("autobyteus.cli")
    cli_logger.setLevel(script_log_level)
    cli_logger.propagate = True
    
    logger.info(f"Core library logs (excluding CLI) redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")

# --- Environment Variable Checks ---
def check_required_env_vars():
    """Checks for environment variables required by this example and returns them."""
    required_vars = {
        "script_path": "TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH",
        "google_client_id": "GOOGLE_CLIENT_ID",
        "google_client_secret": "GOOGLE_CLIENT_SECRET",
        "google_refresh_token": "GOOGLE_REFRESH_TOKEN",
    }
    env_values = {}
    missing_vars = []
    for key, var_name in required_vars.items():
        value = os.environ.get(var_name)
        if not value:
            missing_vars.append(var_name)
        else:
            env_values[key] = value
    if missing_vars:
        logger.error("This example requires the following environment variables to be set: %s", missing_vars)
        sys.exit(1)
    if not Path(env_values["script_path"]).exists():
        logger.error(f"The script path specified by TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH does not exist: {env_values['script_path']}")
        sys.exit(1)
    return env_values

async def main(args: argparse.Namespace):
    """Main function to configure and run the GoogleSlidesAgent."""
    logger.info("--- Starting Google Slides Agent Example ---")
    env_vars = check_required_env_vars()

    # 1. Instantiate all the core MCP and registry components.
    config_service = McpConfigService()
    conn_manager = McpConnectionManager(config_service=config_service)
    schema_mapper = McpSchemaMapper()
    tool_registry = default_tool_registry
    
    registrar = McpToolRegistrar(
        config_service=config_service,
        conn_manager=conn_manager,
        schema_mapper=schema_mapper,
        tool_registry=tool_registry
    )

    # 2. Define the configuration for the MCP server.
    server_id = "google-slides-mcp"
    tool_prefix = "gslides"
    google_slides_mcp_config = {
        server_id: {
            "transport_type": "stdio",
            "command": "node",
            "args": [env_vars["script_path"]],
            "enabled": True,
            "tool_name_prefix": tool_prefix,
            "env": {
                "GOOGLE_CLIENT_ID": env_vars["google_client_id"],
                "GOOGLE_CLIENT_SECRET": env_vars["google_client_secret"],
                "GOOGLE_REFRESH_TOKEN": env_vars["google_refresh_token"],
            }
        }
    }
    config_service.load_configs(google_slides_mcp_config)

    # The `finally` block ensures the connection manager cleans up resources
    try:
        # 3. Discover and register tools from the configured server.
        logger.info("Discovering and registering remote Google Slides tools...")
        await registrar.discover_and_register_tools()
        logger.info("Remote tool registration complete.")

        # 4. Create tool instances from the registry for our agent.
        all_tool_names = tool_registry.list_tool_names()
        gslides_tool_names = [name for name in all_tool_names if name.startswith(tool_prefix)]
        if not gslides_tool_names:
            logger.error("No Google Slides tools were found in the registry after discovery. Cannot create agent.")
            return

        logger.info(f"Creating instances for registered Google Slides tools: {gslides_tool_names}")
        tools_for_agent = [tool_registry.create_tool(name) for name in gslides_tool_names]
        
        # 5. Configure and create the agent.
        try:
            _ = LLMModel[args.llm_model]
        except (ValueError, KeyError):
            logger.error(f"LLM Model '{args.llm_model}' is not valid. Available models: {[m.value for m in LLMModel]}")
            sys.exit(1)

        logger.info(f"Creating LLM instance for model: {args.llm_model}")
        llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

        system_prompt = (
            "You are a helpful assistant with expertise in creating and managing Google Slides presentations.\n"
            "You have access to a set of specialized tools for this purpose.\n\n"
            "When asked to create a presentation, you should use the 'gslides_create_presentation' tool.\n"
            "When asked to add content, you should find out what kind of content and use the 'gslides_batch_update_presentation' tool with the correct request objects.\n"
            "When asked to summarize a presentation, use the 'gslides_summarize_presentation' tool.\n\n"
            "Here are the tools available to you:\n"
            "{{tools}}\n\n"
            "Here are some examples of how to use them:\n"
            "{{tool_examples}}"
        )

        gslides_agent_config = AgentConfig(
            name="GoogleSlidesAgent",
            role="GoogleSlidesExpert",
            description="An agent that can create and manage Google Slides presentations using a set of remote tools.",
            llm_instance=llm_instance,
            system_prompt=system_prompt,
            tools=tools_for_agent,
            auto_execute_tools=True,  # For simplicity, tools will execute without asking for approval.
            use_xml_tool_format=True
        )

        agent = default_agent_factory.create_agent(config=gslides_agent_config)
        logger.info(f"Google Slides Agent instance created: {agent.agent_id}")

        # 6. Run the agent in an interactive CLI session.
        logger.info(f"Starting interactive session for agent {agent.agent_id}...")
        await agent_cli.run(agent=agent)
        logger.info(f"Interactive session for agent {agent.agent_id} finished.")

    except Exception as e:
        logger.error(f"An error occurred during the agent workflow: {e}", exc_info=True)
    finally:
        # 7. Clean up all MCP connections.
        logger.info("Cleaning up MCP connections...")
        await conn_manager.cleanup()
        logger.info("Cleanup complete.")
        logger.info("--- Google Slides Agent Example Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the GoogleSlidesAgent interactively.")
    parser.add_argument("--llm-model", type=str, default="GPT_4o_API", help=f"The LLM model to use. Call --help-models for list.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    
    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized() 
            print("Available LLM Models:")
            model_names = [m.name for m in LLMModel] if LLMModel else []
            for model_name in sorted(model_names): print(f"  - {model_name}")
        except Exception as e: print(f"Error listing models: {e}")
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
