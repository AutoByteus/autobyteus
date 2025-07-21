#!/usr/bin/env python3
"""
Simple Twitter Scraping Agent

This script creates a basic agent that can interact with websites.
It demonstrates how to create an agent and send it instructions for web scraping.
"""

import asyncio
import logging
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_simple_twitter_agent():
    """
    Creates and runs a simple agent for web interaction.
    """
    
    try:
        # Initialize the LLM Factory
        LLMFactory.ensure_initialized()
        
        # Get an LLM instance
        llm_instance = LLMFactory.create_llm("gpt-4o")
        
        # Get the agent factory
        factory = AgentFactory()
        
        print("Creating simple web interaction agent...")
        
        # Define the agent configuration
        agent_config = AgentConfig(
            name="SimpleWebAgent",
            role="web_assistant", 
            description="A simple agent that can help with web-related tasks",
            llm_instance=llm_instance,
            system_prompt="""You are a helpful web assistant. You can help users with various web-related tasks and provide information about websites and web scraping approaches.

If the user asks about web scraping or browser automation:
1. Explain the general approach they would need to take
2. Mention the tools they would need (like browser automation tools)
3. Provide step-by-step instructions
4. Include important considerations about ethics and legality

Always be helpful and provide detailed, actionable advice.""",
            tools=[],  # Will use available tools
            auto_execute_tools=True,
            use_xml_tool_format=False
        )
        
        # Create the agent
        agent = factory.create_agent(agent_config)
        agent_id = agent.agent_id
        
        print(f"Agent created successfully with ID: {agent_id}")
        
        # Start the agent
        if not agent.is_running:
            agent.start()
            await asyncio.sleep(1)
        
        # Define the task
        task_message = """I want to scrape information from X.com (Twitter) about Elon Musk's profile. Specifically, I need:

1. His profile name and handle (@username)
2. His bio/description
3. Recent tweet content (first few tweets)
4. Follower count if visible

Can you help me understand how to do this using browser automation tools? Please provide:
- A step-by-step approach
- What tools I would need
- The specific sequence of actions
- Important considerations about doing this ethically

If you have access to browser automation tools like browser_navigate, browser_click, browser_type, browser_snapshot, and browser_screenshot, please use them to demonstrate the process. Otherwise, just provide detailed instructions."""
        
        # Send the message
        message = AgentInputUserMessage(content=task_message)
        
        print("Sending task to agent...")
        await agent.post_user_message(message)
        
        # Monitor responses
        print("Agent is processing the request...")
        print("=" * 60)
        
        event_stream = AgentEventStream(agent)
        
        response_count = 0
        max_responses = 10
        
        async for event in event_stream.all_events():
            response_count += 1
            
            if hasattr(event, 'data') and hasattr(event.data, 'content'):
                print(f"Agent Response {response_count}:")
                print(event.data.content)
                print("-" * 40)
            elif hasattr(event, 'content') and event.content:
                print(f"Agent Response {response_count}:")
                print(event.content)
                print("-" * 40)
            
            if response_count >= max_responses:
                print("Reached maximum responses")
                break
        
        # Stop the agent
        await agent.stop()
        print("Agent stopped successfully")
        
        # Clean up the thread pool manager
        from autobyteus.agent.runtime.agent_thread_pool_manager import AgentThreadPoolManager
        try:
            thread_manager = AgentThreadPoolManager()
            thread_manager.shutdown(wait=True)
        except Exception:
            # Ignore cleanup errors
            pass
        
    except Exception as e:
        logger.error(f"Error running simple Twitter agent: {e}", exc_info=True)
        raise

def main():
    """Main entry point."""
    try:
        asyncio.run(run_simple_twitter_agent())
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main() 