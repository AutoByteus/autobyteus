# File: tests/integration_tests/agent/research_summary_workflow.py

import asyncio
from autobyteus.agent.group.agent_group import AgentGroup
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.group.coordinator_agent import CoordinatorAgent
from autobyteus.llm.rpa.gemini_llm import GeminiLLM
from autobyteus.llm.rpa.mistral_llm import MistralLLM
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch

async def setup_agent_group():
    agent_group = AgentGroup()

    # Set up ResearchAgent
    research_llm = MistralLLM()
    research_prompt = PromptBuilder("You are a research assistant. Use the GoogleSearch tool to find information.")
    research_tools = [GoogleSearch()]
    research_agent = GroupAwareAgent("ResearchAgent", research_prompt, research_llm, research_tools)

    # Set up SummaryAgent
    summary_llm = GeminiLLM()
    summary_prompt = PromptBuilder("You are a summarization assistant. Summarize the information sent to you.")
    summary_agent = GroupAwareAgent("SummaryAgent", summary_prompt, summary_llm, [])

    # Add agents to the group
    agent_group.add_agent(research_agent)
    agent_group.add_agent(summary_agent)

    # Set up CoordinatorAgent
    coordinator_llm = MistralLLM()
    coordinator_tools = []  # The coordinator will use the SendMessageTo tool added by GroupAwareAgent
    coordinator_agent = CoordinatorAgent("CoordinatorAgent", coordinator_llm, coordinator_tools)
    agent_group.set_coordinator_agent(coordinator_agent)

    return agent_group

async def run_workflow():
    agent_group = await setup_agent_group()
    
    # Start the workflow with a user query
    user_task = "Research the impact of artificial intelligence on healthcare and provide a summary."
    result = await agent_group.run(user_task)
    print("Final result:", result)

if __name__ == "__main__":
    asyncio.run(run_workflow())