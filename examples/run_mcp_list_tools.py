# file: autobyteus/examples/run_mcp_list_tools.py
"""
This example script demonstrates how to use the McpToolRegistrar to connect
to a remote MCP server and list the available tools without registering or
executing them.

This is a "dry-run" or "preview" operation, useful for inspecting the
capabilities of a remote MCP server.
"""
import asyncio
import logging
import sys
import os
import json
import argparse
from pathlib import Path
from typing import List

# --- Boilerplate to make the script runnable from the project root ---

# Ensure the autobyteus package is discoverable
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

# --- Imports for the MCP Client Example ---

try:
    from autobyteus.tools.mcp import McpToolRegistrar
    from autobyteus.tools.registry import ToolDefinition
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)

# --- Basic Logging Setup ---
logger = logging.getLogger("mcp_list_tools_example")

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
    """Checks for environment variables required by the SQLite MCP server."""
    required_vars = {
        "script_path": "TEST_SQLITE_MCP_SCRIPT_PATH",
        "db_path": "TEST_SQLITE_DB_PATH",
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
        logger.error("Example usage in your .env file:")
        logger.error('TEST_SQLITE_MCP_SCRIPT_PATH="/path/to/mcp-database-server/dist/src/index.js"')
        logger.error('TEST_SQLITE_DB_PATH="/path/to/your/database.db"')
        sys.exit(1)

    script_path_obj = Path(env_values["script_path"])
    if not script_path_obj.exists():
        logger.error(f"The script path specified by TEST_SQLITE_MCP_SCRIPT_PATH does not exist: {script_path_obj}")
        sys.exit(1)

    db_path_obj = Path(env_values["db_path"])
    if not db_path_obj.exists():
        logger.error(f"The database path specified by TEST_SQLITE_DB_PATH does not exist: {db_path_obj}")
        logger.error("Please ensure the database file is created before running this script.")
        sys.exit(1)
        
    return env_values

def print_tool_definitions(tool_definitions: List[ToolDefinition]):
    """Iterates through a list of tool definitions and prints their JSON schema."""
    print("\n--- Discovered Remote Tool Schemas (from ToolDefinition) ---")
    for tool_definition in sorted(tool_definitions, key=lambda d: d.name):
        try:
            # get_usage_json() provides a provider-agnostic JSON schema representation
            tool_json_schema = tool_definition.get_usage_json()
            print(f"\n# Tool: {tool_definition.name}")
            print(f"  Description: {tool_definition.description}")
            print("# Schema (JSON):")
            # Pretty-print the JSON schema
            print(json.dumps(tool_json_schema, indent=2))
        except Exception as e:
            print(f"\n# Tool: {tool_definition.name}")
            print(f"  Error getting schema from definition: {e}")
    print("\n--------------------------------------------------------\n")


async def main():
    """
    Main function to connect to the SQLite MCP server and list its tools.
    """
    logger.info("--- Starting MCP Remote Tool Listing Example ---")
    
    env_vars = check_required_env_vars()
    
    # 1. Instantiate the McpToolRegistrar.
    registrar = McpToolRegistrar()

    # 2. Define the configuration for the SQLite MCP server.
    server_id = "sqlite-mcp"
    sqlite_mcp_config_dict = {
        server_id: {
            "transport_type": "stdio",
            "stdio_params": {
                "command": "node",
                "args": [
                    env_vars["script_path"],
                    env_vars["db_path"],
                ],
                "env": {}, # No specific env vars needed for the SQLite server itself
            },
            "enabled": True,
            "tool_name_prefix": "sqlite",
        }
    }

    try:
        # 3. Use the registrar's `list_remote_tools` method for a preview.
        # This connects to the server, lists tools, and disconnects without
        # adding them to the main tool registry.
        logger.info(f"Connecting to remote server '{server_id}' to preview available tools...")
        
        tool_definitions = await registrar.list_remote_tools(mcp_config=sqlite_mcp_config_dict)
        
        # 4. Print the results.
        if tool_definitions:
            print_tool_definitions(tool_definitions)
            logger.info(f"Successfully listed {len(tool_definitions)} tools from the remote server.")
        else:
            logger.warning("No tools were found on the remote server.")

    except Exception as e:
        logger.error(f"An error occurred while trying to list remote tools: {e}", exc_info=True)
    
    logger.info("--- MCP Remote Tool Listing Example Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List available tools from the remote SQLite MCP server.")
    parser.add_argument("--debug", action="store_true", help="Enable debug level logging on the console.")
    args = parser.parse_args()
    
    setup_logging(debug=args.debug)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as e:
        # Gracefully handle user interruption or normal exit.
        if isinstance(e, SystemExit) and e.code == 0:
             logger.info("Script exited normally.")
        else:
             logger.warning(f"Script interrupted ({type(e).__name__}). Exiting.")
    except Exception as e:
        logger.error(f"An unhandled error occurred at the top level: {e}", exc_info=True)
