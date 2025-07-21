# Twitter/X.com Scraping with Browseruse MCP Server

This directory contains examples of how to create and use agents with browseruse MCP server tools to scrape Twitter/X.com for profile information.

## Overview

The examples demonstrate how to:
1. Create an agent definition with browseruse tools
2. Use the agent to navigate to X.com
3. Search for "elon musk" 
4. Click on the first result
5. Extract profile information and recent tweets

## Prerequisites

1. **Browseruse MCP Server**: You need to have the browseruse MCP server configured and running
2. **Agent Definition**: The `TwitterScrapingAgent` with ID 5 should be created (done automatically by running the examples)
3. **LLM Access**: You need access to an LLM (GPT-4, Claude, etc.)

## Files

### 1. `twitter_scraping_simple.py`
**Purpose**: Educational example showing the step-by-step process
**Usage**: 
```bash
python examples/twitter_scraping_simple.py
```
This script shows you the sequence of browser automation steps and provides detailed instructions you can send to any agent.

### 2. `twitter_scraping_agent.py`  
**Purpose**: Direct agent creation and execution
**Usage**:
```bash
python examples/twitter_scraping_agent.py
```
This creates an agent directly using the AgentFactory and runs the scraping task.

### 3. `twitter_scraping_server_agent.py`
**Purpose**: Server-based agent execution using the agent definition
**Usage**:
```bash
python examples/twitter_scraping_server_agent.py
```
This uses the server's agent instance manager to create and run the agent.

## Agent Definition Created

The examples use an agent definition with the following tools from browseruse MCP server:
- `browser_navigate` - Navigate to URLs
- `browser_click` - Click on web elements  
- `browser_type` - Type text into input fields
- `browser_snapshot` - Capture page accessibility tree
- `browser_screenshot` - Take screenshots
- `browser_wait` - Wait for specified time
- `browser_go_back` / `browser_go_forward` - Navigation
- `browser_hover` - Hover over elements
- `browser_select_option` - Select dropdown options
- `browser_press_key` - Press keyboard keys
- `browser_get_console_logs` - Get browser console logs

## Expected Workflow

1. **Navigate**: Agent goes to https://x.com
2. **Snapshot**: Takes accessibility snapshot to understand page structure
3. **Search**: Finds search box, types "elon musk", presses Enter
4. **Results**: Waits for results, takes another snapshot
5. **Profile**: Clicks on first result (Elon Musk's profile)
6. **Extract**: Takes final snapshot and screenshot, extracts information
7. **Report**: Provides structured summary of found information

## Sample Output Format

The agent will provide output like:
```
TWITTER PROFILE SCRAPING RESULTS
================================

Profile Information:
- Name: Elon Musk
- Handle: @elonmusk
- Bio: [Profile description text]
- Followers: [Count if visible]
- Following: [Count if visible]

Recent Tweets:
1. [First tweet content]
2. [Second tweet content]  
3. [Third tweet content]

Notes: [Any observations or issues]
```

## Configuration

### LLM Model
Update the `llm_model_name` variable in the scripts to match your available models:
- `"gpt-4"`
- `"gpt-3.5-turbo"`
- `"claude-3-sonnet"`
- etc.

### Tool Execution
Set `auto_execute_tools` to:
- `True` - Agent executes tools automatically
- `False` - Manual approval required for each tool

### Timeout and Limits
Adjust in the scripts:
- `timeout` - Maximum runtime (default: 300 seconds)
- `max_responses` - Maximum agent responses (default: 20-25)

## Error Handling

The examples include error handling for:
- Agent creation failures
- LLM model unavailability  
- Tool execution errors
- Network timeouts
- Browser automation issues

## Important Notes

1. **Rate Limiting**: Twitter/X.com may rate limit or block automated access
2. **Login Requirements**: Some content may require login
3. **Terms of Service**: Respect Twitter's ToS and robots.txt
4. **Dynamic Content**: Page structures may change over time
5. **Browser State**: Browseruse maintains browser state between tool calls

## Troubleshooting

### Common Issues

1. **Agent Definition Not Found**: Ensure the TwitterScrapingAgent (ID: 5) exists
2. **Tools Not Available**: Verify browseruse MCP server is running and connected
3. **LLM Model Error**: Check your LLM configuration and API keys
4. **Browser Automation Fails**: Twitter may have changed their page structure
5. **Rate Limiting**: Try adding longer wait times between actions

### Debugging

Enable debug logging by adding:
```python
logging.basicConfig(level=logging.DEBUG)
```

Monitor browser console logs using:
```python
# In your agent instructions
await agent.use_tool("browser_get_console_logs")
```

## Extending the Examples

You can modify these examples to:
- Scrape different profiles or search terms
- Extract additional information (tweets, media, etc.)
- Handle login flows
- Navigate to specific tweet threads
- Extract trending topics
- Monitor for new tweets

## Legal and Ethical Considerations

- Always respect website terms of service
- Don't overload servers with too many requests
- Consider using official APIs when available
- Be transparent about automated access
- Respect user privacy and content rights 