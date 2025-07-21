#!/usr/bin/env python3
"""
Twitter/X.com Scraping Agent Example (Server-based)

This script demonstrates how to use the server-based agent execution system
to run the TwitterScrapingAgent we created with agent definition ID 5.
"""

import asyncio
import logging
import time
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_twitter_scraping_with_server():
    """
    Creates and runs a Twitter scraping agent using the direct agent creation approach.
    """
    
    # Initialize the LLM Factory
    LLMFactory.ensure_initialized()
    
    # Get an LLM instance (adjust model name as needed)
    llm_instance = LLMFactory.create_llm("gpt-4o")  # or other available models
    
    # Get the agent factory
    factory = AgentFactory()
    
    print("Creating agent instance for Twitter scraping...")
    
    try:
        # Define the agent configuration with browseruse tools
        agent_config = AgentConfig(
            name="TwitterScrapingAgent",
            role="web_scraper", 
            description="An agent capable of navigating Twitter/X.com and extracting content",
            llm_instance=llm_instance,
            system_prompt="""You are a web scraping agent equipped with browser automation tools. 
Your task is to navigate websites, interact with web elements, and extract information.

When given a task to scrape a website:
1. First navigate to the target URL using browser_navigate
2. Take a snapshot to understand the page structure using browser_snapshot
3. Interact with elements as needed (clicking, typing, etc.)
4. Extract the requested information
5. Provide a clear summary of what you found

Always be respectful of website terms of service and rate limits.""",
            tools=[],  # Tools will be loaded automatically based on available tools
            auto_execute_tools=True,  # Set to False if you want manual approval for each tool
            use_xml_tool_format=False
        )
        
        # Create the agent using the factory
        agent = factory.create_agent(agent_config)
        agent_id = agent.agent_id
        
        print(f"Agent instance created successfully with ID: {agent_id}")
        
        # Define the scraping task
        task_message = """Please help me scrape information from X.com (formerly Twitter). Here's what I need you to do:

1. Navigate to x.com
2. Search for "elon musk" in the search box  
3. Click on the first result (likely Elon Musk's profile)
4. Take a screenshot of the page
5. Collect and extract the following information:
   - Profile name and handle
   - Bio/description text  
   - Recent tweet content (first few tweets visible)
   - Follower count if visible

Please provide a structured summary of the information you collect.

Important notes:
- Use browser_navigate to go to x.com
- Use browser_snapshot to understand page structure before interacting
- Use browser_type to enter search terms
- Use browser_click to click on elements
- Use browser_screenshot to capture the final result
- Be patient and wait for pages to load using browser_wait if needed"""
        
        # Start the agent if not already running
        if not agent.is_running:
            agent.start()
            await asyncio.sleep(1)  # Give the agent time to start
        
        # Send the task message
        message = AgentInputUserMessage(content=task_message)
        
        print("Sending task to agent...")
        await agent.post_user_message(message)
        
        # Monitor the agent's progress
        print("Agent is working on the task...")
        print("=" * 60)
        
        # Create an event stream to monitor responses
        event_stream = AgentEventStream(agent)
        
        response_count = 0
        max_responses = 25  # Increased limit for complex tasks
        start_time = time.time()
        timeout = 300  # 5 minutes timeout
        
        async for event in event_stream.all_events():
            response_count += 1
            current_time = time.time()
            
            if hasattr(event, 'data') and hasattr(event.data, 'content'):
                print(f"Agent Response {response_count} (at {current_time - start_time:.1f}s):")
                print(event.data.content)
                print("-" * 40)
            elif hasattr(event, 'content') and event.content:
                print(f"Agent Response {response_count} (at {current_time - start_time:.1f}s):")
                print(event.content)
                print("-" * 40)
            
            # Check timeout
            if current_time - start_time > timeout:
                print("Task timeout reached")
                break
                
            # Break if we've received enough responses
            if response_count >= max_responses:
                print("Reached maximum responses limit")
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
        logger.error(f"Error running Twitter scraping agent: {e}", exc_info=True)
        raise

def main():
    """Main entry point for the script."""
    try:
        asyncio.run(run_twitter_scraping_with_server())
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main() 