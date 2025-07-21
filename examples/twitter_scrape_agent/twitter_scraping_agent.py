#!/usr/bin/env python3
"""
Twitter/X.com Scraping Agent Example

This script demonstrates how to create and use an agent with browseruse MCP server tools
to navigate to X.com, search for "elon musk", click on the first result, and collect text.
"""

import asyncio
import logging
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_twitter_scraping_agent():
    """
    Creates and runs an agent that can scrape Twitter/X.com using browser automation.
    """
    
    # Initialize the LLM Factory
    LLMFactory.ensure_initialized()
    
    # Get an LLM instance (adjust model name as needed)
    llm_instance = LLMFactory.create_llm("gpt-4")  # or "claude-3-sonnet" or other available models
    
    # Define the agent configuration
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
        tools=[],  # Tools will be loaded from the agent definition
        auto_execute_tools=True,  # Set to False if you want manual approval for each tool
        use_xml_tool_format=False
    )
    
    # Create the agent using the factory
    factory = AgentFactory()
    agent = factory.create_agent(agent_config)
    
    # Create an event stream to capture agent responses
    event_stream = AgentEventStream(agent.agent_id)
    
    # Start the agent
    agent.start()
    
    # Define the task message
    task_message = AgentInputUserMessage(
        content="""Please help me scrape information from X.com (formerly Twitter). Here's what I need you to do:

1. Navigate to x.com
2. Search for "elon musk" in the search box
3. Click on the first result (likely Elon Musk's profile)
4. Take a screenshot of the page
5. Collect and extract the following information:
   - Profile name and handle
   - Bio/description text
   - Recent tweet content (first few tweets visible)
   - Follower count if visible
   
Please provide a structured summary of the information you collect."""
    )
    
    # Send the message to the agent
    await agent.post_user_message(task_message)
    
    # Listen for responses from the agent
    print("Agent is working on the task...")
    print("=" * 60)
    
    response_count = 0
    max_responses = 20  # Limit responses to prevent infinite loop
    
    async for event in event_stream:
        response_count += 1
        
        if hasattr(event, 'content'):
            print(f"Agent Response {response_count}:")
            print(event.content)
            print("-" * 40)
        
        # Break if we've received enough responses or the agent seems done
        if response_count >= max_responses:
            print("Reached maximum responses limit")
            break
    
    # Stop the agent
    await agent.stop()
    print("Agent stopped successfully")

def main():
    """Main entry point for the script."""
    try:
        asyncio.run(run_twitter_scraping_agent())
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        logger.error(f"Error running Twitter scraping agent: {e}", exc_info=True)

if __name__ == "__main__":
    main() 