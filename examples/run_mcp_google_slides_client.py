import asyncio
import logging
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import AsyncIterator, Optional, List

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
    # High-level components for the full workflow
    from autobyteus.tools.mcp import McpToolRegistrar
    from autobyteus.tools.registry import ToolRegistry, default_tool_registry, ToolDefinition
    from autobyteus.agent.context import AgentContext, AgentConfig, AgentRuntimeState
    from autobyteus.llm.base_llm import BaseLLM
    from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
logger = logging.getLogger("mcp_agent_runner")

# --- Dummy LLM for creating AgentContext ---
class DummyLLM(BaseLLM):
    """A dummy LLM implementation required to instantiate AgentConfig."""
    def __init__(self):
        # We need to provide a model and config to the BaseLLM constructor.
        # Let's use a dummy model configuration.
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.utils.llm_config import LLMConfig
        from autobyteus.llm.llm_factory import default_llm_factory

        # Ensure factory is initialized to access models
        default_llm_factory.ensure_initialized()

        # Pick any existing model for the dummy, e.g., the first one available.
        try:
            # Iterating through LLMModel is now possible due to metaclass
            dummy_model_instance = next(iter(LLMModel))
        except StopIteration:
            # This is a fallback in case no models are registered, which is unlikely but safe.
            raise RuntimeError("No LLMModels are registered in the factory. Cannot create DummyLLM.")
        
        super().__init__(model=dummy_model_instance, llm_config=LLMConfig())

    def configure_system_prompt(self, system_prompt: str):
        # This is on BaseLLM. My no-op implementation is fine.
        super().configure_system_prompt(system_prompt)

    async def _send_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        """Dummy implementation for sending a message."""
        logger.debug("DummyLLM._send_user_message_to_llm called.")
        return CompleteResponse(content="This is a dummy response from a dummy LLM.", usage=None)

    async def _stream_user_message_to_llm(
        self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs
    ) -> AsyncIterator[ChunkResponse]:
        """Dummy implementation for streaming a message."""
        logger.debug("DummyLLM._stream_user_message_to_llm called.")
        yield ChunkResponse(content="This is a dummy response from a dummy LLM.", is_complete=True, usage=None)


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

def print_tool_definitions(tool_definitions: List[ToolDefinition]):
    """Iterates through a list of tool definitions and prints their JSON schema."""
    print("\n--- Registered Tool Schemas (from ToolDefinition) ---")
    for tool_definition in sorted(tool_definitions, key=lambda d: d.name):
        try:
            tool_json_schema = tool_definition.get_usage_json()
            print(f"\n# Tool: {tool_definition.name}")
            print(json.dumps(tool_json_schema, indent=2))
        except Exception as e:
            print(f"\n# Tool: {tool_definition.name}")
            print(f"  Error getting schema from definition: {e}")
    print("\n--------------------------------------------------------\n")


async def main():
    """
    Main function to set up and run the Google Slides agent.
    """
    logger.info("--- Starting Google Slides Agent using MCP ---")
    
    env_vars = check_required_env_vars()
    
    # 1. Instantiate the core MCP and registry components.
    tool_registry = default_tool_registry
    registrar = McpToolRegistrar()

    # 2. Define the configuration for the MCP server as a dictionary.
    server_id = "google-slides-mcp"
    google_slides_mcp_config_dict = {
        server_id: {
            "transport_type": "stdio",
            "stdio_params": {
                "command": "node",
                "args": [env_vars["script_path"]],
                "env": {
                    "GOOGLE_CLIENT_ID": env_vars["google_client_id"],
                    "GOOGLE_CLIENT_SECRET": env_vars["google_client_secret"],
                    "GOOGLE_REFRESH_TOKEN": env_vars["google_refresh_token"],
                }
            },
            "enabled": True,
            "tool_name_prefix": "gslides",
        }
    }

    try:
        # 3. Discover and register tools by passing the config dictionary directly.
        logger.info(f"Performing targeted discovery for remote tools from server '{server_id}'...")
        await registrar.discover_and_register_tools(mcp_config=google_slides_mcp_config_dict)
        registered_tool_defs = registrar.get_registered_tools_for_server(server_id)
        logger.info(f"Tool registration complete. Discovered tools: {[t.name for t in registered_tool_defs]}")

        # 4. Create an instance of a specific tool using the ToolRegistry.
        create_tool_name = "gslides_create_presentation"
        summarize_tool_name = "gslides_summarize_presentation"
        
        if create_tool_name not in tool_registry.list_tool_names():
            logger.error(f"Tool '{create_tool_name}' was not found in the registry. Aborting.")
            return

        logger.info(f"Creating an instance of the '{create_tool_name}' tool from the registry...")
        create_presentation_tool = tool_registry.create_tool(create_tool_name)
        
        logger.info(f"Creating an instance of the '{summarize_tool_name}' tool from the registry...")
        summarize_presentation_tool = tool_registry.create_tool(summarize_tool_name)

        # 5. Execute the tool using its standard .execute() method.
        presentation_title = f"AutoByteUs E2E Demo - {datetime.now().isoformat()}"
        logger.info(f"Executing '{create_tool_name}' with title: '{presentation_title}'")
        
        dummy_llm = DummyLLM()
        dummy_config = AgentConfig(
            name="mcp_example_runner_agent",
            role="tool_runner",
            description="A dummy agent config for running tools outside of a full agent.",
            llm_instance=dummy_llm,
            system_prompt="N/A",
            tools=[]
        )
        dummy_state = AgentRuntimeState(agent_id="mcp_example_runner")
        dummy_context = AgentContext(agent_id="mcp_example_runner", config=dummy_config, state=dummy_state)
        
        create_result = await create_presentation_tool.execute(
            context=dummy_context,
            title=presentation_title
        )
        
        if not isinstance(create_result, str):
            raise ValueError(f"Unexpected result type from tool '{create_tool_name}'. Expected a JSON string. Got: {type(create_result)}")

        presentation_object = json.loads(create_result)
        actual_presentation_id = presentation_object.get("presentationId")

        if not actual_presentation_id:
            raise ValueError(f"Could not find 'presentationId' in the response. Response: {create_result[:200]}...")

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
        
        if not isinstance(summary_result, str):
            raise ValueError(f"Unexpected result type from tool '{summarize_tool_name}'. Got: {type(summary_result)}")

        logger.info(f"Tool '{summarize_tool_name}' executed successfully.")
        print("\n--- Presentation Summary ---")
        print(summary_result)
        print("--------------------------\n")
        
        # 7. Print all tool schemas for verification
        print_tool_definitions(registered_tool_defs)

    except Exception as e:
        logger.error(f"An error occurred during the workflow: {e}", exc_info=True)
    
    logger.info("--- MCP Integration Workflow Example Finished ---")


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
