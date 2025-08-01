#!/usr/bin/env python3
"""
Final Google Slides CLI
A simplified script to run an agent that can create and manage Google Slides presentations,
with special focus on proper input prompt handling.
"""
import asyncio
import logging
import sys
import os
import argparse
from pathlib import Path
import re
import json
from typing import Tuple, Optional, Dict, Any
from abc import ABC, abstractmethod
import xml.etree.ElementTree as ET

# Ensure the autobyteus package is discoverable
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))

# Configure logging to stderr to avoid interfering with stdout prompts
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("google_slides_cli")

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    env_file_path = PACKAGE_ROOT / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path)
        print(f"Loaded environment variables from: {env_file_path}", file=sys.stderr)
    else:
        print(f"No .env file found at: {env_file_path}", file=sys.stderr)
except ImportError:
    print("Warning: python-dotenv not installed.", file=sys.stderr)

def check_required_env_vars() -> Dict[str, str]:
    """Check and return required environment variables."""
    env_vars = {}
    
    # Check for optional .env file and load it
    dotenv_path = PACKAGE_ROOT / ".env"
    if dotenv_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path)
            print(f"Loaded environment variables from: {dotenv_path}")
        except ImportError:
            print("Warning: .env file found but python-dotenv is not installed.")
    
    # Check Google API credentials which will be needed for API calls
    for var in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]:
        value = os.getenv(var)
        if not value:
            logger.warning(f"Environment variable {var} is not set. Some Google API features may not work.")
        else:
            env_vars[var] = value
            
    return env_vars

# Custom LLM Response Processor base class to avoid import issues
class BaseLLMResponseProcessor(ABC):
    """
    Simplified version of BaseLLMResponseProcessor just for this script
    """
    def get_name(self) -> str:
        """
        Returns the unique registration name for this processor.
        Defaults to the class name.
        """
        return self.__class__.__name__
        
    @abstractmethod
    async def process_response(self, response: str, context, triggering_event) -> bool:
        """Process an LLM response and return whether it was handled"""
        pass

# Add this class before the main function
class PythonCodeRejector(BaseLLMResponseProcessor):
    """
    A response processor that rejects Python code responses and forces the agent to use XML tool calls.
    """
    async def process_response(self, response: str, context, triggering_event) -> bool:
        # Check if the response contains Python code but not XML tool calls
        has_python_code = bool(re.search(r'def\\s+\\w+\\s*\\(|import\\s+\\w+|from\\s+\\w+\\s+import|\\w+\\(\\w+\\s*=|^\\s*\\w+\\s*=\\s*\\w+\\(', response))
        has_xml_tool = '<tool_code>' in response and '</tool_code>' in response and '<command name="' in response
        
        # If there's no XML tool but there's what looks like code or a function call, reject it
        if (has_python_code or "(" in response) and not has_xml_tool:
            # Response contains Python code but not XML tool calls - reject it
            rejection_message = (
                "I notice you're trying to write Python code directly. "
                "Please use the XML tool format instead. For example:\n\n"
                "<tool_code>\n"
                "<command name=\"gslides_create_presentation\">\n"
                "    <arg name=\"title\">My Presentation</arg>\n"
                "    <arg name=\"user_google_email\">user@example.com</arg>\n"
                "</command>\n"
                "</tool_code>"
            )
            
            logger.warning(f"Rejected non-XML tool response: {response[:100]}...")
            # Set the rejection in context so handlers can send the rejection to the user
            context.set_rejector_message(rejection_message)
            return True
            
        return False

# Custom XML Tool Processor to parse XML tool commands
class XMLToolProcessor(BaseLLMResponseProcessor):
    """
    A processor that handles XML-formatted tool commands and executes them
    """
    def __init__(self):
        self.xml_pattern = re.compile(r'<tool_code>\s*(.*?)\s*</tool_code>', re.DOTALL)
    
    async def process_response(self, response: str, context, triggering_event) -> bool:
        # Parse tool code with more flexibility
        # Clean up markdown formatting first (remove backticks and any code block indicators)
        response_text = re.sub(r'```(?:tool_code)?|```', '', response)
            
        # Check if the response has the opening tag but incorrectly formatted
        if '<tool_code>' not in response_text and 'tool_code>' in response_text:
            response_text = response_text.replace('tool_code>', '<tool_code>')
            
        # Check if the response has the closing tag but incorrectly formatted
        if '</tool_code>' not in response_text and '/tool_code>' in response_text:
            response_text = response_text.replace('/tool_code>', '</tool_code>')

        # Extract tool code between tags
        matches = self.xml_pattern.findall(response_text)
        if not matches:
            return False
            
        xml_content = matches[0]
        logger.info(f"Found XML tool code: {xml_content[:100]}...")
        
        try:
            # Parse the XML manually using regex for better robustness
            command_match = re.search(r'<command\s+name=["\'](.*?)["\']', xml_content)
            if not command_match:
                logger.error("Could not find command name in XML")
                return False
                
            tool_name = command_match.group(1)
            
            # Remove the tool prefix if it exists (e.g. gslides_create_presentation -> create_presentation)
            if tool_name.startswith('gslides_'):
                tool_name = tool_name[len('gslides_'):]
            
            # Extract all args
            args = {}
            arg_pattern = r'<arg\s+name=["\'](.*?)["\']\s*>(.*?)</arg>'
            for arg_match in re.finditer(arg_pattern, xml_content, re.DOTALL):
                arg_name = arg_match.group(1)
                arg_value = arg_match.group(2).strip()
                args[arg_name] = arg_value
            
            if not args:
                logger.error("No arguments found in XML tool call")
                return False
                
            logger.info(f"Parsed XML tool call: {tool_name} with args: {args}")
            
            # Create a tool invocation request and add it to the context
            from autobyteus.agent.message.agent_input_tool_invocation import AgentInputToolInvocationRequest
            tool_invocation = AgentInputToolInvocationRequest(
                tool_name=tool_name,
                parameters=args,
                raw_request=xml_content
            )
            context.handle_tool_invocation_request(tool_invocation)
            
            return True
        except Exception as e:
            logger.error(f"Error parsing XML tool call: {e}", exc_info=True)
            return False

async def warm_up_connection(session):
    """Pre-warm and test the connection by listing tools"""
    max_attempts = 3
    for i in range(max_attempts):
        try:
            # Send a ping to validate the connection
            tools_result = await session.list_tools()
            logger.info(f"Successfully listed {len(tools_result.tools)} tools: {[t.name for t in tools_result.tools]}")
            return True
        except Exception as e:
            logger.warning(f"Connection attempt {i+1}/{max_attempts} failed: {e}")
            await asyncio.sleep(1)
    return False

async def main(args):
    """Main function to set up and run the Google Slides agent."""
    conn_manager = None
    try:
        # Import required components
        from autobyteus.agent.context.agent_config import AgentConfig
        from autobyteus.llm.llm_factory import default_llm_factory
        from autobyteus.agent.factory.agent_factory import default_agent_factory
        from autobyteus.cli import agent_cli # Use the standard CLI runner
        from autobyteus.tools.mcp import (
            McpConfigService, McpConnectionManager, McpSchemaMapper, McpToolRegistrar
        )
        from autobyteus.tools.registry import default_tool_registry
        from autobyteus.llm.utils.llm_config import LLMConfig
        
        # Try to patch the isinstance check for BaseLLMResponseProcessor
        try:
            import builtins
            _original_isinstance = builtins.isinstance
            
            def patched_isinstance(obj, classinfo):
                # If checking against the framework's BaseLLMResponseProcessor and obj is our custom processor, return True
                if hasattr(obj, 'get_name') and hasattr(obj, 'process_response'):
                    if str(classinfo).find('BaseLLMResponseProcessor') >= 0:
                        return True
                # Otherwise use the original isinstance
                return _original_isinstance(obj, classinfo)
            
            # Replace the built-in isinstance with our patched version
            builtins.isinstance = patched_isinstance
            logger.info("Successfully patched isinstance to handle custom processors")
        except Exception as e:
            logger.warning(f"Failed to patch isinstance: {e}. Custom processors may not work correctly.")
        
        # Get environment variables
        env_vars = check_required_env_vars()
        _original_isinstance_saved = _original_isinstance

        # Set up MCP components
        logger.info("Setting up MCP components...")
        config_service = McpConfigService()
        conn_manager = McpConnectionManager(config_service=config_service)
        schema_mapper = McpSchemaMapper()
        
        # Configure the MCP server
        server_id = "google-slides-mcp-ws"
        tool_prefix = "gslides"
        mcp_config = {
            server_id: {
                "transport_type": "websocket",
                "uri": "ws://localhost:8765",
                "enabled": True,
                "tool_name_prefix": tool_prefix,
            }
        }
        config_service.load_configs(mcp_config)
        
        # Register tools
        registrar = McpToolRegistrar(
            config_service=config_service,
            conn_manager=conn_manager,
            schema_mapper=schema_mapper,
            tool_registry=default_tool_registry
        )
        
        # Connect to MCP server
        logger.info("Connecting to MCP server...")
        try:
            session = await conn_manager.get_session(server_id)
            
            # Force reconnect to ensure it's fresh
            await session.transport_strategy.disconnect()
            await session.transport_strategy.connect()
            
            # Warm up the connection
            is_warmed = await warm_up_connection(session)
            if not is_warmed:
                logger.error("Could not establish a working connection to Google Slides MCP server")
                return
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}", exc_info=True)
            return

        # Discover and register tools
        logger.info("Discovering Google Slides tools...")
        try:
            await registrar.list_and_register_remote_tools(server_id)
        except Exception as e:
            logger.error(f"Failed to register MCP tools: {e}", exc_info=True)
            return

        # Filter for Google Slides tools
        tool_instances = [tool for tool in default_tool_registry.get_all_tools() if tool.get_name().startswith('gslides_')]
        if not tool_instances:
            logger.error(f"No Google Slides tools found. Cannot continue.")
            return

        # Create tool instances
        tool_instances = [default_tool_registry.create_tool(name) for name in tool_instances]
        logger.info(f"Created {len(tool_instances)} tool instances")
        
        # Set up the agent
        system_prompt = (
            "You are a helpful assistant that can create and manage Google Slides presentations.\n\n"
            "⚠️ CRITICAL INSTRUCTION ⚠️\n"
            "You MUST ONLY use the XML tool format shown below when interacting with Google Slides.\n"
            "NEVER generate Python code, functions, or import statements.\n"
            "NEVER use ```python blocks or any other code blocks.\n"
            "ALWAYS wrap your tool calls in <tool_code> tags.\n\n"
            "You must ask the user for their Google email address ('user_google_email') if it's not provided, as it is a required parameter for all tools.\n\n"
            "✅ CORRECT FORMAT (ALWAYS USE THIS):\n"
            "<tool_code>\n"
            "<command name=\"gslides_create_presentation\">\n"
            "    <arg name=\"title\">My Presentation Title</arg>\n"
            "    <arg name=\"user_google_email\">user@example.com</arg>\n"
            "</command>\n"
            "</tool_code>\n\n"
            "❌ INCORRECT FORMAT (NEVER USE THIS):\n"
            "```python\n"
            "def create_presentation(title, user_email):\n"
            "    # Don't write code like this\n"
            "    pass\n"
            "```\n\n"
            "Available Google Slides tools:\n" + 
            "\n".join([f"- {tool.get_name()}" for tool in tool_instances])
        )
        
        # Create LLM instance
        llm_instance = default_llm_factory.create_llm(
            model_identifier=args.llm_model,
            llm_config=LLMConfig(temperature=0.2)  # Lower temperature for more deterministic responses
        )
        
        # Create the Python code rejector
        python_code_rejector = PythonCodeRejector()
        logger.info("Initialized PythonCodeRejector")
        
        # Create the XML tool processor
        xml_tool_processor = XMLToolProcessor()
        logger.info("Initialized XMLToolProcessor")
        
        # Configure and create the agent
        agent_config = AgentConfig(
            name="GoogleSlidesAgent",
            role="Google Slides Assistant",
            description="An agent that helps users create and manage Google Slides presentations.",
            llm_instance=llm_instance,
            system_prompt=system_prompt,
            tools=tool_instances,
            auto_execute_tools=False,  # Always require approval
            use_xml_tool_format=True,
            llm_response_processors=[xml_tool_processor, python_code_rejector]
        )
        
        agent = default_agent_factory.create_agent(config=agent_config)
        logger.info(f"Agent created: {agent.agent_id}")
        
        logger.info("Agent created, starting CLI runner...")
        if args.initial_prompt:
            await agent.send_message(args.initial_prompt)
            
        # Start the agent CLI
        await agent_cli.run(agent)
    
    except ImportError as e:
        logger.error(f"Error importing autobyteus components: {e}")
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nSession interrupted by user.")
    except Exception as e:
        logger.error(f"An unhandled error occurred in main: {e}", exc_info=True)
    finally:
        # The agent_cli.run() function handles stopping the agent.
        # We only need to cleanup resources created in *this* script, like the MCP connection.
        if conn_manager:
            try:
                await conn_manager.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}", exc_info=True)
        
        # Restore the original isinstance function
        try:
            import builtins
            if '_original_isinstance_saved' in locals():
                builtins.isinstance = _original_isinstance_saved
                logger.info("Restored original isinstance function")
        except Exception as e:
            logger.warning(f"Failed to restore original isinstance: {e}")
        
        logger.info("Session ended.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an agent that interacts with Google Slides.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--initial-prompt", type=str, help="Initial prompt to send to the agent.")
    parser.add_argument("--llm-model", type=str, default="claude-3-opus-20240229", help="The LLM model to use.")
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("autobyteus").setLevel(logging.DEBUG)
    
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1) 