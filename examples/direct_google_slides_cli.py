#!/usr/bin/env python3
"""
Direct Google Slides CLI script.
This script uses direct stdin/stdout handling for user input instead of relying on agent_cli.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Ensure the autobyteus package is discoverable
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))

# Configure basic logging to stderr to avoid interfering with stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("direct_google_slides_cli")

try:
    # Import minimal required components
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
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

def print_with_flush(text, file=sys.stdout):
    """Print text and flush the specified file descriptor."""
    file.write(text)
    file.flush()

def check_required_env_vars():
    """Check for required environment variables."""
    required_vars = {
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
        print(f"Missing required environment variables: {', '.join(missing_vars)}", file=sys.stderr)
        sys.exit(1)
    
    # Use the Python MCP script from the examples directory
    mcp_script_path = SCRIPT_DIR / "test_google_slides_mcp_script.py"
    if not mcp_script_path.exists():
        print(f"MCP script not found at: {mcp_script_path}", file=sys.stderr)
        sys.exit(1)
    
    env_values["script_path"] = str(mcp_script_path)
    return env_values

async def setup_agent():
    """Set up the Google Slides agent with MCP tools."""
    env_vars = check_required_env_vars()
    
    # Set up MCP components
    logger.info("Setting up MCP components...")
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
    
    try:
        # Discover and register tools
        logger.info("Discovering Google Slides tools...")
        await registrar.discover_and_register_tools()
        registered_tools = tool_registry.list_tool_names()
        logger.info(f"Registered tools: {registered_tools}")

        if not any(name.startswith(tool_prefix) for name in registered_tools):
            logger.error(f"No tools with prefix '{tool_prefix}' were registered. Cannot proceed.")
            await conn_manager.cleanup()
            sys.exit(1)

        # Create tool instances for the agent
        mcp_tool_instances = [
            tool_registry.create_tool(name) for name in registered_tools if name.startswith(tool_prefix)
        ]

        # Set up the agent with the registered tools
        system_prompt = (
            "You are a helpful assistant that can create and manage Google Slides presentations.\n\n"
            "When a user asks to perform an action with Google Slides, you must use the appropriate tool.\n"
            "You must ask the user for their Google email address ('user_google_email') if it's not provided, "
            "as it is a required parameter for all tools to associate the action with a user.\n\n"
            "Available tools:\n"
            "{{tools}}\n\n"
            "{{tool_examples}}"
        )

        # Create the LLM instance
        llm_instance = default_llm_factory.create_llm(model_identifier=LLMModel.GEMINI_2_0_FLASH_API)

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
        logger.info(f"Agent created with {len(mcp_tool_instances)} tools")
        
        return agent, conn_manager
        
    except Exception as e:
        logger.error(f"Error setting up agent: {e}")
        await conn_manager.cleanup()
        sys.exit(1)

class DirectCLIManager:
    """Manages the direct CLI interaction with the agent."""
    
    def __init__(self, agent):
        self.agent = agent
        self.agent_has_spoken = False
        self.pending_approval_data = None
        self.turn_complete = asyncio.Event()
        self.streamer = AgentEventStream(agent)
        self.event_task = None
    
    async def start(self):
        """Start the agent and event processing."""
        if not self.agent.is_running:
            self.agent.start()
        
        # Start event processing
        self.event_task = asyncio.create_task(self.process_events())
        
        # Wait for agent to initialize
        await self.turn_complete.wait()
        self.turn_complete.clear()
    
    async def process_events(self):
        """Process events from the agent."""
        try:
            async for event in self.streamer.all_events():
                await self.handle_event(event)
        except asyncio.CancelledError:
            logger.info("Event processing task cancelled.")
        except Exception as e:
            logger.error(f"Error in event processing: {e}")
        finally:
            logger.debug("Event processing task finished.")
            self.turn_complete.set()  # Ensure main loop isn't stuck
    
    async def handle_event(self, event):
        """Handle a single event from the agent."""
        if event.event_type == StreamEventType.ASSISTANT_CHUNK and isinstance(event.data, AssistantChunkData):
            if not self.agent_has_spoken:
                print_with_flush("\nAgent: ")
                self.agent_has_spoken = True
            
            print_with_flush(event.data.content)
            
        elif event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE and isinstance(event.data, AssistantCompleteResponseData):
            if not self.agent_has_spoken:
                print(f"\nAgent: {event.data.content}")
            
            print()  # Add a newline after complete response
            self.agent_has_spoken = False
            
        elif event.event_type == StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED and isinstance(event.data, ToolInvocationApprovalRequestedData):
            self.pending_approval_data = event.data
            try:
                args_str = str(event.data.arguments)
                print(f"\nTool Call: '{event.data.tool_name}' requests permission to run with arguments:\n{args_str}")
                print_with_flush("Approve? (y/n): ")
            except Exception as e:
                logger.error(f"Error formatting tool approval request: {e}")
            
        elif event.event_type == StreamEventType.AGENT_IDLE:
            logger.info("Agent is now idle.")
            self.turn_complete.set()
    
    async def run_interactive_session(self):
        """Run the interactive session."""
        print("\n=== GOOGLE SLIDES AGENT INTERACTIVE SESSION ===")
        print("Type your messages after the 'You: ' prompt.")
        print("Type '/exit' or '/quit' to end the session.\n")
        
        try:
            while True:
                if self.pending_approval_data:
                    # Handle tool approval
                    loop = asyncio.get_event_loop()
                    approval_input = await loop.run_in_executor(None, sys.stdin.readline)
                    approval_input = approval_input.strip().lower()
                    
                    approval_data = self.pending_approval_data
                    self.pending_approval_data = None
                    
                    is_approved = approval_input in ["y", "yes"]
                    reason = "User approved via CLI" if is_approved else "User denied via CLI"
                    
                    await self.agent.post_tool_execution_approval(approval_data.invocation_id, is_approved, reason)
                    self.turn_complete.clear()
                    await self.turn_complete.wait()
                
                else:
                    # Handle user input - CRITICAL FIX: Use direct console output for prompt
                    # This ensures the prompt is always visible
                    print_with_flush("You: ")
                    
                    # Use direct input reading to ensure prompt is displayed
                    loop = asyncio.get_event_loop()
                    user_input = await loop.run_in_executor(None, lambda: input())
                    
                    if user_input.lower() in ["/quit", "/exit"]:
                        print("Exiting session...")
                        break
                    
                    if not user_input:
                        continue
                    
                    # Send message to agent
                    self.agent_has_spoken = False
                    self.turn_complete.clear()
                    await self.agent.post_user_message(AgentInputUserMessage(content=user_input))
                    await self.turn_complete.wait()
        
        except KeyboardInterrupt:
            print("\nSession interrupted by user.")
        except Exception as e:
            logger.error(f"Error in interactive session: {e}")
        finally:
            if self.event_task and not self.event_task.done():
                self.event_task.cancel()
                try:
                    await self.event_task
                except asyncio.CancelledError:
                    pass  # Expected
    
    async def close(self):
        """Close the CLI manager."""
        if self.event_task and not self.event_task.done():
            self.event_task.cancel()
            try:
                await self.event_task
            except asyncio.CancelledError:
                pass  # Expected
        
        if self.agent.is_running:
            await self.agent.stop()
        
        await self.streamer.close()

async def main():
    """Main function."""
    agent = None
    conn_manager = None
    cli_manager = None
    
    try:
        # Set up the agent
        agent, conn_manager = await setup_agent()
        
        # Create and start the CLI manager
        cli_manager = DirectCLIManager(agent)
        await cli_manager.start()
        
        # Run the interactive session
        await cli_manager.run_interactive_session()
        
    finally:
        # Clean up
        if cli_manager:
            await cli_manager.close()
        
        if conn_manager:
            logger.info("Cleaning up connections...")
            await conn_manager.cleanup()
        
        logger.info("Session ended.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession interrupted by user.")
    except Exception as e:
        print(f"Unhandled error: {e}", file=sys.stderr)
        sys.exit(1) 