# Twitter/X.com Scraping with AutoByteus

This directory contains examples and instructions for creating and using an agent to scrape Twitter/X.com using browseruse MCP server tools.

## 🎯 Overview

We've successfully created a **TwitterScrapingAgent** (ID: 5) that can:
- Navigate to X.com
- Search for "elon musk" 
- Click on profile results
- Extract profile information (name, handle, bio, tweets, follower counts)
- Take screenshots and snapshots for verification

## ✅ What's Been Set Up

### Agent Definition Created
- **Agent ID**: 5
- **Name**: TwitterScrapingAgent
- **Role**: web_scraper
- **Tools**: All 12 browseruse MCP server tools
- **Status**: ✅ Ready to use

### Available Browseruse Tools
The agent has access to these browser automation tools:
1. `browser_navigate` - Navigate to URLs
2. `browser_click` - Click on web elements  
3. `browser_type` - Type text into input fields
4. `browser_snapshot` - Capture page accessibility tree
5. `browser_screenshot` - Take screenshots
6. `browser_wait` - Wait for specified time
7. `browser_go_back/browser_go_forward` - Navigation
8. `browser_hover` - Hover over elements
9. `browser_select_option` - Select dropdown options
10. `browser_press_key` - Press keyboard keys
11. `browser_get_console_logs` - Get browser console logs

## 🚀 **RECOMMENDED: Using Web Interface**

The easiest and most reliable way to use the TwitterScrapingAgent:

### Quick Start
1. Open your AutoByteus web interface
2. Go to the **Agents** section
3. Find **TwitterScrapingAgent** (ID: 5)
4. Create a new session/conversation
5. Send this message:

```
Please help me scrape information from X.com (Twitter). Here's what I need:

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

Important: Be patient with loading times and handle any popups or login prompts gracefully.
```

### What to Expect
- Real-time tool execution monitoring
- Visual feedback of browser actions
- Screenshots and snapshots displayed
- Structured output with extracted data

## 📁 Example Files

### ✅ Working Examples

**`web_interface_instructions.py`** - **RECOMMENDED**
```bash
python examples/twitter_scrape_agent/web_interface_instructions.py
```
- Complete step-by-step guide for using the web interface
- Exact message to send to the agent
- Troubleshooting tips

**`instructions_only.py`** - **WORKING**
```bash
python examples/twitter_scrape_agent/instructions_only.py
```
- Displays comprehensive instructions and process overview
- Shows expected output format
- Educational reference

**`twitter_scraping_simple.py`** - **WORKING**
```bash
python examples/twitter_scrape_agent/twitter_scraping_simple.py
```
- Step-by-step breakdown of the scraping process
- Shows tool usage patterns
- Educational reference

### ⚠️ Development Examples

**`simple_twitter_agent.py`** - **DEVELOPMENT**
```bash
python examples/twitter_scrape_agent/simple_twitter_agent.py
```
- Creates agent programmatically
- Limited tools (no browseruse MCP tools available in this context)
- Provides general web scraping advice

**`twitter_scraping_server_agent.py`** - **DEVELOPMENT**
```bash  
python examples/twitter_scrape_agent/twitter_scraping_server_agent.py
```
- Alternative programmatic approach
- Similar limitations to simple version

## 🎯 Expected Output

When the TwitterScrapingAgent successfully completes the task:

```
TWITTER PROFILE SCRAPING RESULTS
================================

Profile Information:
- Name: Elon Musk
- Handle: @elonmusk
- Bio: [Profile description]
- Followers: [Count if visible]
- Following: [Count if visible]

Recent Tweets:
1. [Tweet content]
2. [Tweet content]
3. [Tweet content]

Screenshots: [List of screenshots taken]
Notes: [Any observations or issues encountered]
```

## 🔧 Prerequisites

1. **Browseruse MCP Server**: Must be running and connected to AutoByteus
2. **Agent Definition**: TwitterScrapingAgent (ID: 5) is already created
3. **LLM Access**: GPT-4, Claude, or compatible model
4. **Web Interface**: AutoByteus web application running

## 🔧 Troubleshooting

### Agent Not Found
- Verify TwitterScrapingAgent (ID: 5) exists in your agent list
- Check that you're looking in the correct agents section

### No Browseruse Tools Available
- Ensure browseruse MCP server is running and connected
- Check MCP server configuration in AutoByteus settings
- Restart MCP server if needed

### Agent Gives Generic Advice
- This indicates the agent doesn't have access to browseruse tools
- Use the web interface with the pre-created agent (ID: 5) instead

### X.com Login Required
- The agent should handle login prompts gracefully
- Some content may require authentication
- Agent will note when login is required

## ⚠️ Important Considerations

- **Legal Compliance**: Respect Twitter's Terms of Service
- **Rate Limiting**: Agent includes appropriate delays between actions
- **Privacy**: Be mindful of personal data extraction
- **Ethical Use**: Use responsibly and with proper permissions

## 🏆 Success Checklist

- [ ] TwitterScrapingAgent (ID: 5) visible in agent list
- [ ] Browseruse MCP server running and connected  
- [ ] Can create session with the agent
- [ ] Agent responds to task message
- [ ] See tool executions (browser_navigate, browser_click, etc.)
- [ ] Agent provides structured output with extracted data

## 🚀 Get Started Now

**The fastest way to start scraping:**
1. Run: `python examples/twitter_scrape_agent/web_interface_instructions.py`
2. Follow the displayed instructions
3. Use the web interface with TwitterScrapingAgent (ID: 5)
4. Send the provided task message
5. Monitor real-time execution and results! 