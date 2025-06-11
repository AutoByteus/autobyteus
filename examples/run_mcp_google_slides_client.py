import asyncio
import logging
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

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
    from autobyteus.tools.mcp import McpConfigService, McpConnectionManager
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)

# --- Basic Logging Setup ---
# A logger for this script
logger = logging.getLogger("mcp_client_example")

def setup_logging(debug: bool = False):
    """Configures logging for the script.
    
    Args:
        debug (bool): If True, sets the logging level to DEBUG. Otherwise, INFO.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers to avoid duplicate messages
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    # Configure the logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        stream=sys.stdout,
    )
    
    # If in debug mode, also set the autobyteus library logger to DEBUG
    if debug:
        logging.getLogger("autobyteus").setLevel(logging.DEBUG)
        logger.info("Debug logging enabled.")
    else:
        # Keep library logs at a higher level to reduce noise
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
        logger.error("This example requires the following environment variables to be set:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("Please set them in your environment or in the .env file at the project root.")
        sys.exit(1)
        
    if not Path(env_values["script_path"]).exists():
        logger.error(f"The script path specified by TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH does not exist: {env_values['script_path']}")
        sys.exit(1)

    return env_values

async def main():
    """
    Main function to configure and run the MCP client for the Google Slides server.
    """
    logger.info("--- Starting MCP Google Slides Client Example ---")
    
    env_vars = check_required_env_vars()
    
    # 1. Instantiate the core AutoByteUs MCP services.
    # McpConfigService loads and manages server configurations.
    # McpConnectionManager uses these configs to create and manage connections.
    config_service = McpConfigService()
    conn_manager = McpConnectionManager(config_service=config_service)

    # 2. Define the configuration for the MCP server.
    # This is the same configuration structure used in the integration test.
    # The server_id "google-slides-mcp" is a unique key for this connection.
    google_slides_mcp_config = {
        "google-slides-mcp": {
            "transport_type": "stdio",
            "command": "node",
            "args": [env_vars["script_path"]],
            "enabled": True,
            "tool_name_prefix": "gslides", # Optional: prefixes all tool names, e.g., "gslides_create_presentation"
            "env": {
                "GOOGLE_CLIENT_ID": env_vars["google_client_id"],
                "GOOGLE_CLIENT_SECRET": env_vars["google_client_secret"],
                "GOOGLE_REFRESH_TOKEN": env_vars["google_refresh_token"],
            }
        }
    }

    # 3. Load the configuration into the service.
    config_service.load_configs(google_slides_mcp_config)
    logger.info("Loaded MCP server configuration for 'google-slides-mcp'.")

    # The `finally` block ensures the connection manager cleans up resources
    # (i.e., terminates the Node.js server subprocess) even if an error occurs.
    try:
        # 4. Get a client session from the connection manager.
        # This will start the server subprocess and establish communication.
        logger.info("Establishing connection to the MCP server...")
        session = await conn_manager.get_session("google-slides-mcp")
        logger.info("Connection successful!")

        # 5. List the tools available on the remote server.
        list_tools_result = await session.list_tools()
        tool_names = [tool.name for tool in list_tools_result.tools]
        logger.info(f"Discovered {len(tool_names)} tools on the server: {tool_names}")

        # 6. Call a remote tool: `create_presentation`.
        presentation_title = f"AutoByteUs MCP Client Demo - {datetime.now().isoformat()}"
        logger.info(f"Calling tool 'create_presentation' with title: '{presentation_title}'")
        
        create_result = await session.call_tool(
            "create_presentation",
            {"title": presentation_title}
        )
        
        # The tool returns the full presentation object as a JSON string.
        # We need to parse it to extract the ID.
        presentation_response_text = create_result.content[0].text
        presentation_object = json.loads(presentation_response_text)
        actual_presentation_id = presentation_object.get("presentationId")

        if not actual_presentation_id:
            raise ValueError(f"Could not find 'presentationId' in the response from 'create_presentation'. Response: {presentation_response_text[:200]}...")

        logger.info(f"Tool 'create_presentation' executed. Extracted Presentation ID: {actual_presentation_id}")

        # 7. Use the extracted ID in a second tool call: `summarize_presentation`.
        logger.info(f"Calling tool 'summarize_presentation' for presentation ID: {actual_presentation_id}")
        
        summary_result = await session.call_tool(
            "summarize_presentation",
            {"presentationId": actual_presentation_id}
        )
        
        presentation_summary = summary_result.content[0].text
        logger.info(f"Tool 'summarize_presentation' executed successfully.")
        print("\n--- Presentation Summary ---")
        print(presentation_summary)
        print("--------------------------\n")

    except Exception as e:
        logger.error(f"An error occurred during MCP interaction: {e}", exc_info=True)
    finally:
        # 8. Clean up all connections.
        logger.info("Cleaning up MCP connections...")
        await conn_manager.cleanup()
        logger.info("Cleanup complete.")
        logger.info("--- MCP Google Slides Client Example Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an MCP client to interact with the Google Slides MCP server.")
    parser.add_argument("--debug", action="store_true", help="Enable debug level logging on the console.")
    args = parser.parse_args()
    
    setup_logging(debug=args.debug)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code == 0:
             logger.info("Script exited normally.")
        else:
             logger.info(f"Script interrupted ({type(e).__name__}). Exiting.")
    except Exception as e:
        logger.error(f"An unhandled error occurred at the top level: {e}", exc_info=True)
