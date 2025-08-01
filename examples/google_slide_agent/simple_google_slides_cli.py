#!/usr/bin/env python3
"""
Simple Google Slides CLI
A minimalist script to run an agent that can create Google Slides presentations,
with enforced XML format for tool calls.
"""
import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import re

# Ensure the autobyteus package is discoverable
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("simple_google_slides_cli")

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

def check_required_env_vars():
    """Check for required environment variables and return them."""
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
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    return env_values

# XML Formatter to force model to use XML syntax
class XMLPromptFormatter:
    """Forces the model to respond with proper XML tool calls."""
    
    @staticmethod
    def format_system_prompt():
        """Return a system prompt that forces XML format."""
        return """You are a specialized assistant that interacts exclusively with Google Slides through XML tool calls.

CRITICAL: You MUST ALWAYS respond using ONLY this EXACT XML format:

<tool_code>
<command name="gslides_create_presentation">
    <arg name="title">My Presentation Title</arg>
    <arg name="user_google_email">user@example.com</arg>
</command>
</tool_code>

Your responses MUST NEVER contain any other content outside of the <tool_code> tags.
Your responses MUST NEVER include explanations, narratives, or any non-XML content.
You MUST ONLY use the exact format shown above with <command> and <arg> tags.

NEVER output plain text, markdown, or any other format.
NEVER provide an outline or suggestions for slides.
NEVER include normal chat responses.

The ONLY valid tool is gslides_create_presentation which requires exactly two arguments:
1. title - The title of the presentation to create
2. user_google_email - The email address of the user

If a user asks to create a presentation, you MUST format the response correctly as XML.
"""

    @staticmethod
    def parse_xml_response(response_text):
        """
        Parse the XML tool call from the response text.
        Returns (tool_name, args_dict) if successful, or (None, None) if parsing fails.
        """
        print("Raw response:", repr(response_text))
        
        # Fallback to manual extraction if the XML parsing fails
        command_match = re.search(r'<command\s+name=["\'](.*?)["\']', response_text)
        if command_match:
            tool_name = command_match.group(1)
            print(f"Found command name: {tool_name}")
            
            # Extract all args
            args = {}
            arg_pattern = r'<arg\s+name=["\'](.*?)["\']\s*>(.*?)</arg>'
            for arg_match in re.finditer(arg_pattern, response_text, re.DOTALL):
                arg_name = arg_match.group(1)
                arg_value = arg_match.group(2).strip()
                args[arg_name] = arg_value
                print(f"Found arg: {arg_name} = {arg_value}")
                
            if args:
                return tool_name, args
        
        # If manual extraction failed, try the original way with clean-up
        # Clean up markdown formatting first (remove backticks and any code block indicators)
        response_text = re.sub(r'```(?:tool_code)?|```', '', response_text)
        
        # Fix opening and closing tags if needed
        if '<tool_code>' not in response_text and 'tool_code>' in response_text:
            response_text = response_text.replace('tool_code>', '<tool_code>')
            
        if '</tool_code>' not in response_text and '/tool_code>' in response_text:
            response_text = response_text.replace('/tool_code>', '</tool_code>')
        
        print("Cleaned response:", repr(response_text))
        
        # Extract content between tool_code tags
        pattern = r'<tool_code>\s*(.*?)\s*</tool_code>'
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        if not matches:
            logger.error("No <tool_code> tags found in response")
            return None, None
            
        xml_content = matches[0]
        logger.info(f"Found XML tool code: {xml_content[:100]}...")
        
        try:
            # Parse the XML
            root = ET.fromstring(f"<root>{xml_content}</root>")
            command_element = root.find(".//command")
            
            if command_element is None:
                logger.error("No <command> element found in XML")
                return None, None
                
            tool_name = command_element.get('name')
            if not tool_name:
                logger.error("Command element missing 'name' attribute")
                return None, None
                
            # Extract arguments
            args = {}
            for arg_element in command_element.findall(".//arg"):
                arg_name = arg_element.get('name')
                if arg_name:
                    args[arg_name] = arg_element.text or ""
                    
            return tool_name, args
            
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return None, None

# This class will handle Google Slides API calls
class GoogleSlidesAPI:
    """Simple wrapper for Google Slides API operations"""
    
    @staticmethod
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
        
    @staticmethod
    async def create_presentation(title, user_email):
        """Create a new Google Slides presentation"""
        logger.info(f"Creating presentation '{title}' for user '{user_email}'")
        
        try:
            from autobyteus.tools.mcp import McpConfigService, McpConnectionManager, McpSchemaMapper
            
            # Set up MCP components
            config_service = McpConfigService()
            conn_manager = McpConnectionManager(config_service=config_service)
            
            # Configure the MCP server
            server_id = "google-slides-mcp-ws"
            mcp_config = {
                server_id: {
                    "transport_type": "websocket",
                    "uri": "ws://localhost:8765",
                    "enabled": True,
                    "tool_name_prefix": "gslides",
                }
            }
            config_service.load_configs(mcp_config)
            
            # Connect to the MCP server
            logger.info(f"Connecting to Google Slides MCP server...")
            session = await conn_manager.get_session(server_id)
            
            # Force reconnect to ensure it's fresh
            await session.transport_strategy.disconnect()
            await session.transport_strategy.connect()
            
            # Warm up the connection
            is_warmed = await GoogleSlidesAPI.warm_up_connection(session)
            if not is_warmed:
                logger.error("Could not establish a working connection to Google Slides MCP server")
                return None
            
            # Call the create_presentation method directly - bypassing the session.is_connected check
            logger.info(f"Calling create_presentation tool with title={title}, user_google_email={user_email}")
            try:
                # Direct call to the transport_strategy rpc_call to bypass the session.is_connected check
                result = await session.transport_strategy.rpc_call(
                    "tools/call",
                    params={
                        "tool_name": "create_presentation",
                        "parameters": {
                            "title": title, 
                            "user_google_email": user_email
                        }
                    }
                )
                
                # Clean up
                await conn_manager.cleanup()
                
                if result and isinstance(result, dict) and "presentationId" in result:
                    presentation_id = result["presentationId"]
                    logger.info(f"Successfully created presentation with ID: {presentation_id}")
                    return presentation_id
                else:
                    logger.error(f"Failed to create presentation. Unexpected result format: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error calling tools/call RPC: {e}", exc_info=True)
                return None
                
        except Exception as e:
            logger.error(f"Error creating presentation: {e}", exc_info=True)
            return None

async def run_command(cmd, args):
    """Execute a command using the proper tool"""
    if cmd == "gslides_create_presentation":
        title = args.get("title")
        email = args.get("user_google_email")
        
        if not title or not email:
            logger.error(f"Missing required arguments. Need 'title' and 'user_google_email', got: {args}")
            return
            
        presentation_id = await GoogleSlidesAPI.create_presentation(title, email)
        if presentation_id:
            print(f"✅ Successfully created presentation: {presentation_id}")
        else:
            print("❌ Failed to create presentation")
    else:
        logger.error(f"Unknown command: {cmd}")

async def main(args):
    """Main function to run the CLI"""
    try:
        # Check environment variables
        check_required_env_vars()
        
        # Import and initialize LLM
        from autobyteus.llm.llm_factory import default_llm_factory
        from autobyteus.llm.utils.llm_config import LLMConfig
        
        llm = default_llm_factory.create_llm(
            model_identifier=args.llm_model,
            llm_config=LLMConfig(temperature=0.01)  # Use extremely low temperature for deterministic responses
        )
        
        if args.initial_prompt:
            # Create a conversation with just the system prompt and user's initial prompt
            system_prompt = XMLPromptFormatter.format_system_prompt()
            
            # Configure the LLM with the system prompt
            llm.configure_system_prompt(system_prompt)
            
            # Send the user message
            print(f"Sending prompt to LLM: {args.initial_prompt}")
            
            # Add few-shot examples to the prompt
            few_shot_examples = """
Example 1:
User: Create a new presentation called "Project Overview"
Assistant: <tool_code>
<command name="gslides_create_presentation">
    <arg name="title">Project Overview</arg>
    <arg name="user_google_email">user@example.com</arg>
</command>
</tool_code>

Example 2:
User: I need a presentation for my Biology class with email john@gmail.com
Assistant: <tool_code>
<command name="gslides_create_presentation">
    <arg name="title">Biology Class</arg>
    <arg name="user_google_email">john@gmail.com</arg>
</command>
</tool_code>

Now, please help with this request:
"""
            
            full_prompt = f"{few_shot_examples}\n{args.initial_prompt}"
            
            from autobyteus.llm.user_message import LLMUserMessage
            user_message = LLMUserMessage(content=full_prompt)
            response = await llm.send_user_message(user_message)
            response_text = response.content
            
            # Parse the XML response
            print(f"Received response: {response_text}")
            tool_name, tool_args = XMLPromptFormatter.parse_xml_response(response_text)
            
            if tool_name and tool_args:
                print(f"Parsed tool call: {tool_name} with args: {tool_args}")
                await run_command(tool_name, tool_args)
            else:
                print("Failed to parse a valid tool call from the response")
        else:
            print("Interactive mode not yet supported. Please provide an --initial-prompt.")
            
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple CLI for Google Slides operations")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--initial-prompt", type=str, help="Initial prompt to send to the LLM")
    parser.add_argument("--llm-model", type=str, default="GEMINI_2_0_FLASH_API", help="The LLM model to use")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        sys.exit(1) 