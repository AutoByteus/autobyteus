# File: autobyteus/examples/research_summary_workflow.py

import asyncio
from autobyteus.agent.agent_group import AgentGroup
from autobyteus.agent.agent import Agent
from autobyteus.agent.group_aware_agent import GroupAwareAgent
from autobyteus.llm.rpa.gemini_llm import GeminiLLM
from autobyteus.llm.rpa.mistral_llm import MistralLLM
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch

async def setup_agent_group():
    agent_group = AgentGroup()

    # Set up ResearchAgent
    research_llm = MistralLLM()
    research_prompt = PromptBuilder("You are a research assistant. Use the GoogleSearch tool to find information, and the MessageSendingTool to send results to the SummaryAgent.")
    research_tools = [GoogleSearch()]
    research_agent = GroupAwareAgent("ResearchAgent", research_prompt, research_llm, research_tools)

    # Set up SummaryAgent
    summary_llm = GeminiLLM()
    summary_prompt = PromptBuilder("You are a summarization assistant. Summarize the information sent to you and use the MessageSendingTool to send the summary back.")
    summary_agent = GroupAwareAgent("SummaryAgent", summary_prompt, summary_llm, [])

    # Add agents to the group
    agent_group.add_agent(research_agent)
    agent_group.add_agent(summary_agent)

    return agent_group

async def run_workflow():
    agent_group = await setup_agent_group()
    
    # Start the workflow with a user query
    result = await agent_group.run()
    print("Final result:", result)

if __name__ == "__main__":
    asyncio.run(run_workflow())