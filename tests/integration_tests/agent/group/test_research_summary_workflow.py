# File: tests/integration_tests/agent/test_research_summary_workflow.py

import pytest
import asyncio
from autobyteus.agent.group.agent_group import AgentGroup
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.group.coordinator_agent import CoordinatorAgent
from autobyteus.llm.rpa.gemini_llm import GeminiLLM
from autobyteus.llm.rpa.groq_llm import GroqLLM, GroqModel

from autobyteus.llm.rpa.mistral_llm import MistralLLM, MistralModel
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch

@pytest.fixture
def agent_group():
    group = AgentGroup()

    # Set up ResearchAgent
    research_llm = GroqLLM(model=GroqModel.LLAMA_3_1_70B_VERSATILE)
    research_prompt = PromptBuilder().from_string("""
    You are a research assistant. Use the GoogleSearch tool to find information.
    
    Available external tools:
    {external_tools}
    """)
    research_tools = [GoogleSearch()]
    research_agent = GroupAwareAgent("ResearchAgent", research_prompt, research_llm, research_tools, skills="google search")

    # Set up SummaryAgent
    summary_llm = GeminiLLM()
    summary_prompt = PromptBuilder().from_string("""
    You are a summarization assistant. Summarize the information sent to you.
    
    Available external tools:
    {external_tools}
    """)
    summary_agent = GroupAwareAgent("SummaryAgent", summary_prompt, summary_llm, [], skills = "summarization")

    # Add agents to the group
    group.add_agent(research_agent)
    group.add_agent(summary_agent)

    # Set up CoordinatorAgent
    coordinator_llm = MistralLLM(model=MistralModel.MISTRAL_LARGE)
    coordinator_tools = []  # The coordinator will use the SendMessageTo tool added by GroupAwareAgent

    coordinator_agent = CoordinatorAgent("CoordinatorAgent", coordinator_llm, coordinator_tools)
    group.set_coordinator_agent(coordinator_agent)

    return group

@pytest.mark.asyncio
async def test_research_summary_workflow(agent_group):
    # Define the user task
    user_task = "Research the impact of artificial intelligence on healthcare and provide a summary."
    
    # Run the workflow
    result = await agent_group.run(user_task)
    
    # Assert the result meets expected criteria
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    assert "artificial intelligence" in result.lower()
    assert "healthcare" in result.lower()

@pytest.mark.asyncio
async def test_agent_group_setup(agent_group):
    assert isinstance(agent_group, AgentGroup)
    assert len(agent_group.agents) == 2
    assert agent_group.coordinator_agent is not None
    assert agent_group.get_agent("ResearchAgent") is not None
    assert agent_group.get_agent("SummaryAgent") is not None

# Add more tests as needed