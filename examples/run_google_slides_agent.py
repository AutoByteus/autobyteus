#!/usr/bin/env python3
"""
Google Slides Agent CLI
A script to run an agent that can create and manage Google Slides presentations.
"""
import asyncio
import logging
import sys
import os
import argparse
from pathlib import Path

# Ensure the autobyteus package is discoverable
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables from .env file if available
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

# Configure logging
logger = logging.getLogger("google_slides_agent")

def setup_logging(debug=False):
    """Configure logging to stderr to avoid interfering with stdout prompts."""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    # Configure logging to stderr
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    
    # Set package logging level
    logging.getLogger("autobyteus").setLevel(log_level)
    
    if debug:
        logger.debug("Debug logging enabled")

def check_required_env_vars():
    """Check for required environment variables and return them."""
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
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Check if script path exists
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
            logger.error(f"Failed to make script executable: {e}")
            sys.exit(1)
    
    return env_values

async def main(args):
    """Main function to set up and run the Google Slides agent."""
    try:
        # Import required components
        from autobyteus.agent.context.agent_config import AgentConfig
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.llm_factory import default_llm_factory
        from autobyteus.agent.factory.agent_factory import default_agent_factory
        from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
        from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
        from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
        from autobyteus.agent.streaming.stream_event_payloads import (
            AssistantChunkData,
            AssistantCompleteResponseData,
            ToolInvocationApprovalRequestedData,
        )
        from autobyteus.tools.mcp import (
            McpConfigService, McpConnectionManager, McpSchemaMapper, McpToolRegistrar
        )
        from autobyteus.tools.registry import default_tool_registry
    except ImportError as e:
        logger.error(f"Error importing autobyteus components: {e}")
        sys.exit(1)
    
    # Check environment variables
    env_vars = check_required_env_vars()
    
    # Set up MCP components
    logger.info("Setting up MCP components...")
    config_service = McpConfigService()
    conn_manager = McpConnectionManager(config_service=config_service)
    schema_mapper = McpSchemaMapper()
    
    # Configure the MCP server
    server_id = "google-slides-mcp-stdio"
    tool_prefix = "gslides"
    mcp_config = {
        server_id: {
            "transport_type": "stdio",
            "command": sys.executable,
            "args": [env_vars["script_path"]],
            "enabled": True,
            "tool_name_prefix": tool_prefix,
            "env": {
                "GOOGLE_CLIENT_ID": env_vars["google_client_id"],
                "GOOGLE_CLIENT_SECRET": env_vars["google_client_secret"],
                "GOOGLE_REFRESH_TOKEN": env_vars["google_refresh_token"],
                "PYTHONPATH": os.environ.get("PYTHONPATH", "")
            }
        }
    }
    config_service.load_configs(mcp_config)
    
    # Create tool registrar
    registrar = McpToolRegistrar(
        config_service=config_service,
        conn_manager=conn_manager,
        schema_mapper=schema_mapper,
        tool_registry=default_tool_registry
    )
    
    try:
        # Discover and register tools
        logger.info("Discovering Google Slides tools...")
        await registrar.discover_and_register_tools()
        registered_tools = default_tool_registry.list_tool_names()
        logger.info(f"Registered tools: {registered_tools}")
        
        if not any(name.startswith(tool_prefix) for name in registered_tools):
            logger.error(f"No tools with prefix '{tool_prefix}' were registered. Cannot proceed.")
            return
        
        # Create tool instances for the agent
        mcp_tool_instances = [
            default_tool_registry.create_tool(name) 
            for name in registered_tools 
            if name.startswith(tool_prefix)
        ]
        
        # Set up the agent
        logger.info("Configuring Google Slides Agent...")
        system_prompt = (
            "You are a helpful assistant that can create and manage Google Slides presentations.\n\n"
            "When a user asks to perform an action with Google Slides, you must use the appropriate tool.\n"
            "You must ask the user for their Google email address ('user_google_email') if it's not provided, "
            "as it is a required parameter for all tools to associate the action with a user.\n\n"
            "Available tools:\n"
            "{{tools}}\n\n"
            "{{tool_examples}}"
        )
        
        # Create LLM instance
        llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)
        
        # Configure the agent
        agent_config = AgentConfig(
            name="GoogleSlidesAgent",
            role="Google Slides Assistant",
            description="An agent that helps users create and manage Google Slides presentations.",
            llm_instance=llm_instance,
            system_prompt=system_prompt,
            tools=mcp_tool_instances,
            auto_execute_tools=False,  # Always require manual approval
            use_xml_tool_format=True
        )
        
        # Create the agent
        agent = default_agent_factory.create_agent(config=agent_config)
        logger.info(f"Agent '{agent.agent_id}' created successfully with {len(mcp_tool_instances)} tools")
        
        # Start the agent
        agent.start()
        
        # Set up event handling
        turn_complete = asyncio.Event()
        agent_has_spoken = False
        pending_approval = None
        
        # Create event streamer
        streamer = AgentEventStream(agent)
        
        # Define event handler
        async def process_events():
            nonlocal agent_has_spoken, pending_approval
            
            try:
                async for event in streamer.all_events():
                    # Handle assistant chunks (streaming responses)
                    if event.event_type == StreamEventType.ASSISTANT_CHUNK and isinstance(event.data, AssistantChunkData):
                        if not agent_has_spoken:
                            sys.stdout.write("\nAgent: ")
                            sys.stdout.flush()
                            agent_has_spoken = True
                        
                        sys.stdout.write(event.data.content)
                        sys.stdout.flush()
                    
                    # Handle complete responses
                    elif event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE and isinstance(event.data, AssistantCompleteResponseData):
                        if not agent_has_spoken:
                            sys.stdout.write(f"\nAgent: {event.data.content}\n")
                            sys.stdout.flush()
                        else:
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                        
                        agent_has_spoken = False
                    
                    # Handle tool approval requests
                    elif event.event_type == StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED and isinstance(event.data, ToolInvocationApprovalRequestedData):
                        pending_approval = event.data
                        args_str = str(event.data.arguments)
                        sys.stdout.write(f"\nTool Call: '{event.data.tool_name}' requests permission to run with arguments:\n{args_str}\n")
                        sys.stdout.write("Approve? (y/n): ")
                        sys.stdout.flush()
                    
                    # Handle agent idle state
                    elif event.event_type == StreamEventType.AGENT_IDLE:
                        logger.debug("Agent is idle")
                        turn_complete.set()
            
            except asyncio.CancelledError:
                logger.debug("Event processing task cancelled")
            except Exception as e:
                logger.error(f"Error in event processing: {e}")
            finally:
                logger.debug("Event processing task finished")
                turn_complete.set()  # Ensure main loop isn't stuck
        
        # Start event processing
        event_task = asyncio.create_task(process_events())
        
        # Wait for agent to initialize
        await turn_complete.wait()
        turn_complete.clear()
        
        # Display welcome message
        print("\n=== GOOGLE SLIDES AGENT INTERACTIVE SESSION ===")
        print("Type your messages after the 'You: ' prompt.")
        print("Type '/exit' or '/quit' to end the session.\n")
        
        # Process initial prompt if provided
        if args.initial_prompt:
            print(f"You: {args.initial_prompt}")
            await agent.post_user_message(AgentInputUserMessage(content=args.initial_prompt))
            turn_complete.clear()
            await turn_complete.wait()
        
        # Main interaction loop
        while True:
            if pending_approval:
                # Handle tool approval
                approval_input = input()  # Direct input for approval
                approval_input = approval_input.strip().lower()
                
                approval_data = pending_approval
                pending_approval = None
                
                is_approved = approval_input in ["y", "yes"]
                reason = "User approved via CLI" if is_approved else "User denied via CLI"
                
                await agent.post_tool_execution_approval(approval_data.invocation_id, is_approved, reason)
            else:
                # Handle user input
                sys.stdout.write("You: ")
                sys.stdout.flush()
                
                user_input = input()  # Direct input for user messages
                
                if user_input.lower() in ["/quit", "/exit"]:
                    print("Exiting session...")
                    break
                
                if not user_input:
                    continue
                
                # Send message to agent
                agent_has_spoken = False
                turn_complete.clear()
                await agent.post_user_message(AgentInputUserMessage(content=user_input))
                await turn_complete.wait()
    
    except KeyboardInterrupt:
        print("\nSession interrupted by user.")
    except Exception as e:
        logger.error(f"Error in interactive session: {e}")
    finally:
        # Clean up
        if 'event_task' in locals() and not event_task.done():
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass
        
        if 'agent' in locals() and agent.is_running:
            await agent.stop()
        
        if 'streamer' in locals():
            await streamer.close()
        
        if conn_manager:
            logger.info("Cleaning up MCP connections...")
            await conn_manager.cleanup()
        
        logger.info("Session ended.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an agent that interacts with Google Slides via MCP.")
    parser.add_argument("--debug", action="store_true", help="Enable debug level logging.")
    parser.add_argument("--initial-prompt", type=str, default=None, help="Initial prompt to send to the agent.")
    parser.add_argument("--llm-model", type=str, default="GEMINI_2_0_FLASH_API", help="The LLM model to use.")
    args = parser.parse_args()
    
    setup_logging(debug=args.debug)
    
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)