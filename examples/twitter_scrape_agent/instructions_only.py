#!/usr/bin/env python3
"""
Twitter/X.com Scraping Instructions

This script provides detailed instructions for creating and using an agent
to scrape Twitter/X.com using browseruse MCP server tools.
"""

def show_twitter_scraping_instructions():
    """
    Display comprehensive instructions for Twitter scraping with browseruse tools.
    """
    
    print("=" * 80)
    print("TWITTER/X.COM SCRAPING WITH BROWSERUSE MCP SERVER")
    print("=" * 80)
    
    print("\n🎯 OBJECTIVE:")
    print("Create an agent that can navigate to X.com, search for 'elon musk',")
    print("click on the first result, and extract profile information.")
    
    print("\n📋 PREREQUISITES:")
    print("1. Browseruse MCP server running and connected")
    print("2. Agent definition with browseruse tools (we created ID: 5)")
    print("3. LLM access (GPT-4, Claude, etc.)")
    
    print("\n🔧 AVAILABLE BROWSERUSE TOOLS:")
    tools = [
        "browser_navigate - Navigate to URLs",
        "browser_click - Click on web elements",
        "browser_type - Type text into input fields",
        "browser_snapshot - Capture page accessibility tree",
        "browser_screenshot - Take screenshots",
        "browser_wait - Wait for specified time",
        "browser_go_back/browser_go_forward - Navigation",
        "browser_hover - Hover over elements",
        "browser_select_option - Select dropdown options",
        "browser_press_key - Press keyboard keys",
        "browser_get_console_logs - Get browser console logs"
    ]
    
    for i, tool in enumerate(tools, 1):
        print(f"  {i:2d}. {tool}")
    
    print("\n📝 STEP-BY-STEP PROCESS:")
    steps = [
        ("Navigate to X.com", "browser_navigate", "https://x.com"),
        ("Take initial snapshot", "browser_snapshot", "Understand page structure"),
        ("Find search box", "browser_click", "Click on search input field"),
        ("Enter search term", "browser_type", "Type 'elon musk'"),
        ("Submit search", "browser_press_key", "Press 'Enter'"),
        ("Wait for results", "browser_wait", "3 seconds"),
        ("Take results snapshot", "browser_snapshot", "See search results"),
        ("Click first profile", "browser_click", "First profile result"),
        ("Wait for profile", "browser_wait", "3 seconds"),
        ("Take final snapshot", "browser_snapshot", "Profile page structure"),
        ("Take screenshot", "browser_screenshot", "Visual capture")
    ]
    
    for i, (action, tool, detail) in enumerate(steps, 1):
        print(f"  {i:2d}. {action}")
        print(f"      Tool: {tool}")
        print(f"      Details: {detail}")
        print()
    
    print("💬 AGENT INSTRUCTION MESSAGE:")
    print("-" * 40)
    instruction = """Please help me scrape information from X.com (Twitter). Here's what I need:

1. Navigate to x.com using browser_navigate
2. Take a snapshot with browser_snapshot to understand the page structure
3. Find and click the search box using browser_click
4. Type "elon musk" using browser_type
5. Press Enter using browser_press_key to search
6. Wait 3 seconds using browser_wait for results to load
7. Take another snapshot to see search results
8. Click on the first profile result (likely Elon Musk's verified profile)
9. Wait 3 seconds for the profile to load
10. Take a final snapshot and screenshot
11. Extract and report:
    - Profile name and handle (@username)
    - Bio/description text
    - Follower/following counts if visible
    - Recent tweet content (first 3-5 tweets)

Please provide a structured summary of all the information you collect.

Important: Be patient with loading times and handle any popups or login prompts gracefully."""
    
    print(instruction)
    print("-" * 40)
    
    print("\n🎯 EXPECTED OUTPUT FORMAT:")
    output_format = """
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

Screenshots: [List of screenshots taken]
Notes: [Any observations or issues encountered]
"""
    print(output_format)
    
    print("\n🚀 HOW TO USE:")
    print("1. In AutoByteus web interface:")
    print("   - Go to Agents section")
    print("   - Find 'TwitterScrapingAgent' (ID: 5)")
    print("   - Create a session with this agent")
    print("   - Send the instruction message above")
    
    print("\n2. Via Python script:")
    print("   - Use examples/twitter_scrape_agent/simple_twitter_agent.py")
    print("   - Or examples/twitter_scrape_agent/twitter_scraping_server_agent.py")
    
    print("\n⚠️  IMPORTANT CONSIDERATIONS:")
    considerations = [
        "Respect Twitter's Terms of Service",
        "Be mindful of rate limiting",
        "Handle login prompts appropriately",
        "Some content may require authentication",
        "Page structures may change over time",
        "Use reasonable delays between actions"
    ]
    
    for consideration in considerations:
        print(f"  • {consideration}")
    
    print("\n✅ SUCCESS INDICATORS:")
    success_indicators = [
        "Agent successfully navigates to x.com",
        "Search functionality works correctly", 
        "Profile page loads and is captured",
        "Data extraction completes without errors",
        "Structured output is provided"
    ]
    
    for indicator in success_indicators:
        print(f"  ✓ {indicator}")
    
    print("\n" + "=" * 80)
    print("Ready to start scraping! Use the agent instruction message above.")
    print("=" * 80)

def main():
    """Main entry point."""
    show_twitter_scraping_instructions()

if __name__ == "__main__":
    main() 