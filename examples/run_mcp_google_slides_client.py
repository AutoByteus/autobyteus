import asyncio
import logging
import sys
import os
import argparse
from pathlib import Path

# --- Boilerplate to make the script runnable from the project root ---
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file_path = PACKAGE_ROOT / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path)
        print(f"Loaded environment variables from: {env_file_path}")
    else:
        print(f"Info: No .env file found at: {env_file_path}.")
except ImportError:
    print("Warning: python-dotenv not installed. Cannot load .env file.")

# --- Imports for AutoByteUs Agent and MCP Client ---
try:
    from autobyteus.tools.mcp import (
        McpConfigService, McpConnectionManager, McpSchemaMapper, McpToolRegistrar
    )
    from autobyteus.tools.registry import default_tool_registry
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.agent.factory.agent_factory import default_agent_factory
    from autobyteus.llm.llm_factory import default_llm_factory
    from autobyteus.llm.models import LLMModel
    from autobyteus.cli import agent_cli
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
logger = logging.getLogger("mcp_agent_runner")

def setup_logging(debug: bool = False):
    """Configures logging for the script."""
    log_level = logging.DEBUG if debug else logging.INFO
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        stream=sys.stdout,
    )
    if debug:
        logging.getLogger("autobyteus").setLevel(logging.DEBUG)
        logger.info("Debug logging enabled.")
    else:
        logging.getLogger("autobyteus").setLevel(logging.INFO)

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
        logger.error(f"This script requires the following environment variables to be set: {missing_vars}")
        sys.exit(1)
    
    script_path_obj = Path(env_values["script_path"])
    if not script_path_obj.exists():
        logger.error(f"The script path specified by TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH does not exist: {script_path_obj}")
        sys.exit(1)
    
    # Ensure the script is executable
    if not os.access(script_path_obj, os.X_OK):
        logger.warning(f"Script at {script_path_obj} is not executable. Attempting to make it executable.")
        try:
            script_path_obj.chmod(script_path_obj.stat().st_mode | 0o111)
            logger.info(f"Made {script_path_obj} executable.")
        except Exception as e:
            logger.error(f"Failed to make script executable: {e}. Please set permissions manually (e.g., `chmod +x {script_path_obj}`).")
            sys.exit(1)

    return env_values

async def main(args: argparse.Namespace):
    """
    Main function to set up and run the Google Slides agent.
    """
    logger.info("--- Starting Google Slides Agent using MCP ---")
    
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

    # 2. Define the configuration for the stdio MCP server.
    server_id = "google-slides-mcp-stdio"
    tool_prefix = "gslides"
    mcp_config = {
        server_id: {
            "transport_type": "stdio",
            # We use the python executable running this script to run the server script
            # This is more robust than relying on a shebang.
            "command": sys.executable,
            "args": [env_vars["script_path"]],
            "enabled": True,
            "tool_name_prefix": tool_prefix,
            "env": {
                "GOOGLE_CLIENT_ID": env_vars["google_client_id"],
                "GOOGLE_CLIENT_SECRET": env_vars["google_client_secret"],
                "GOOGLE_REFRESH_TOKEN": env_vars["google_refresh_token"],
                # Pass python path to subprocess to ensure it can find libraries
                "PYTHONPATH": os.environ.get("PYTHONPATH", "")
            }
        }
    }
    config_service.load_configs(mcp_config)
    logger.info(f"Loaded MCP server configuration for '{server_id}'.")

    try:
        # 3. Discover and register tools from the configured server.
        logger.info("Discovering and registering remote Google Slides tools...")
        await registrar.discover_and_register_tools()
        registered_tools = tool_registry.list_tool_names()
        logger.info(f"Tool registration complete. Available tools in registry: {registered_tools}")

        if not any(name.startswith(tool_prefix) for name in registered_tools):
            logger.error(f"No tools with prefix '{tool_prefix}' were registered. Cannot proceed.")
            logger.error("Please check the MCP server script and its output for errors.")
            return

        # 4. Create tool instances for the agent.
        mcp_tool_instances = [
            tool_registry.create_tool(name) for name in registered_tools if name.startswith(tool_prefix)
        ]

        # 5. Set up the agent.
        logger.info("Configuring Google Slides Agent...")
        system_prompt = (
            "You are a helpful assistant that can create and manage Google Slides presentations.\n"
            "When a user asks to perform an action, you must use the available tools.\n"
            "You must ask the user for their Google email address ('user_google_email') if it's not provided, "
            "as it is a required parameter for all tools to associate the action with a user for logging and accountability.\n\n"
            "Available tools:\n"
            "{{tools}}\n\n"
            "{{tool_examples}}"
        )

        llm_instance = default_llm_factory.create_llm(model_identifier=LLMModel.GEMINI_2_0_FLASH_API)

        agent_config = AgentConfig(
            name="GoogleSlidesAgent",
            role="A helpful assistant for Google Slides",
            description="Manages Google Slides presentations using remote tools via MCP.",
            llm_instance=llm_instance,
            system_prompt=system_prompt,
            tools=mcp_tool_instances,
            auto_execute_tools=False, # Let the user confirm the tool call
            use_xml_tool_format=True
        )

        agent = default_agent_factory.create_agent(config=agent_config)
        logger.info(f"Agent '{agent.agent_id}' created successfully.")

        # 6. Run the agent interactively.
        logger.info("Starting interactive session with the agent...")
        await agent_cli.run(agent=agent)
        logger.info("Interactive session finished.")

    except Exception as e:
        logger.error(f"An error occurred during the agent workflow: {e}", exc_info=True)
    finally:
        # 7. Clean up all connections.
        logger.info("Cleaning up MCP connections...")
        await conn_manager.cleanup()
        logger.info("Cleanup complete.")
        logger.info("--- Google Slides Agent using MCP Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an agent that uses Google Slides tools via MCP.")
    parser.add_argument("--debug", action="store_true", help="Enable debug level logging.")
    args = parser.parse_args()
    
    setup_logging(debug=args.debug)

    try:
        asyncio.run(main(args))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script interrupted. Exiting.")
    except Exception as e:
        logger.error(f"An unhandled error occurred at the top level: {e}", exc_info=True)
