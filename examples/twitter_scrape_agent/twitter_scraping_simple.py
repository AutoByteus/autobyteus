#!/usr/bin/env python3
"""
Simple Twitter/X.com Scraping Example

This script provides a step-by-step example of how to use browseruse tools
to scrape Twitter/X.com for Elon Musk's profile information.
"""

import asyncio
import json
from typing import Dict, Any

# This example assumes you have an agent with browseruse tools available
# You would typically get this agent from your agent management system

async def scrape_twitter_profile_step_by_step():
    """
    Demonstrates the step-by-step process for scraping a Twitter profile.
    This is educational - in practice, you would send these instructions to your agent.
    """
    
    steps = [
        {
            "step": 1,
            "action": "Navigate to X.com",
            "tool": "browser_navigate",
            "params": {"url": "https://x.com"},
            "description": "Go to the X.com homepage"
        },
        {
            "step": 2, 
            "action": "Take initial snapshot",
            "tool": "browser_snapshot",
            "params": {},
            "description": "Capture the page structure to understand layout"
        },
        {
            "step": 3,
            "action": "Find and click search box",
            "tool": "browser_click", 
            "params": {"element": "search input field"},
            "description": "Locate the search input and click to focus it"
        },
        {
            "step": 4,
            "action": "Type search query",
            "tool": "browser_type",
            "params": {"text": "elon musk"},
            "description": "Enter 'elon musk' in the search box"
        },
        {
            "step": 5,
            "action": "Press Enter to search",
            "tool": "browser_press_key",
            "params": {"key": "Enter"},
            "description": "Submit the search query"
        },
        {
            "step": 6,
            "action": "Wait for results to load",
            "tool": "browser_wait",
            "params": {"seconds": 3},
            "description": "Give time for search results to appear"
        },
        {
            "step": 7,
            "action": "Take snapshot of search results",
            "tool": "browser_snapshot",
            "params": {},
            "description": "Capture search results page structure"
        },
        {
            "step": 8,
            "action": "Click on first profile result",
            "tool": "browser_click",
            "params": {"element": "first profile link in search results"},
            "description": "Click on Elon Musk's profile (typically first result)"
        },
        {
            "step": 9,
            "action": "Wait for profile to load",
            "tool": "browser_wait", 
            "params": {"seconds": 3},
            "description": "Allow profile page to fully load"
        },
        {
            "step": 10,
            "action": "Take final snapshot",
            "tool": "browser_snapshot",
            "params": {},
            "description": "Capture the profile page structure for content extraction"
        },
        {
            "step": 11,
            "action": "Take screenshot",
            "tool": "browser_screenshot",
            "params": {},
            "description": "Capture visual screenshot of the profile"
        }
    ]
    
    print("Twitter/X.com Scraping Process - Step by Step")
    print("=" * 50)
    
    for step_info in steps:
        print(f"\nStep {step_info['step']}: {step_info['action']}")
        print(f"Tool: {step_info['tool']}")
        print(f"Description: {step_info['description']}")
        if step_info['params']:
            print(f"Parameters: {json.dumps(step_info['params'], indent=2)}")
        print("-" * 30)

def create_agent_instructions():
    """
    Creates a comprehensive instruction set for an agent to perform Twitter scraping.
    """
    
    instructions = """
You are a web scraping agent with browser automation capabilities. Your task is to navigate to X.com (Twitter), search for "elon musk", and extract profile information.

Follow these steps carefully:

1. **Navigate to X.com**
   - Use browser_navigate with URL: https://x.com
   - Wait for the page to load completely

2. **Understand the page structure**
   - Use browser_snapshot to get the accessibility tree
   - Identify the search input field location

3. **Perform search**
   - Use browser_click to focus on the search input
   - Use browser_type to enter "elon musk"
   - Use browser_press_key with "Enter" to submit search

4. **Handle search results**
   - Use browser_wait for 3 seconds to let results load
   - Use browser_snapshot to see search results structure
   - Identify the first profile result (likely Elon Musk's verified profile)

5. **Navigate to profile**
   - Use browser_click on the first profile result
   - Use browser_wait for 3 seconds for profile to load

6. **Extract information**
   - Use browser_snapshot to get final page structure
   - Use browser_screenshot to capture visual evidence
   - Extract and report:
     * Profile name and handle (@username)
     * Bio/description text
     * Follower/following counts if visible
     * Recent tweet content (first 3-5 tweets)

7. **Provide structured output**
   - Format the extracted information in a clear, structured manner
   - Include any relevant observations about the page

Important considerations:
- Be patient with loading times
- Handle any login prompts or popup dialogs gracefully
- If you encounter rate limiting or blocking, report it clearly
- Respect the website's terms of service
- Take screenshots at key steps for verification

Expected output format:
```
TWITTER PROFILE SCRAPING RESULTS
================================

Profile Information:
- Name: [Full display name]
- Handle: [Username with @]
- Bio: [Profile description]
- Followers: [Count if visible]
- Following: [Count if visible]

Recent Tweets:
1. [Tweet content]
2. [Tweet content]
3. [Tweet content]

Notes: [Any observations or issues encountered]
```

Begin the task when ready.
"""
    
    return instructions.strip()

def main():
    """Main function to demonstrate the scraping approach."""
    
    print("Twitter/X.com Scraping Agent Setup")
    print("=" * 40)
    
    # Show the step-by-step process
    asyncio.run(scrape_twitter_profile_step_by_step())
    
    print("\n\nAgent Instructions:")
    print("=" * 40)
    print(create_agent_instructions())
    
    print("\n\nTo use this with your agent:")
    print("1. Create an agent with browseruse MCP server tools")
    print("2. Send the above instructions as a message to your agent")
    print("3. Monitor the agent's responses and tool usage")
    print("4. The agent will execute the browser automation steps")

if __name__ == "__main__":
    main() 