# File: tests/integration_tests/agent/test_research_summary_workflow.py

import pytest
import asyncio
from autobyteus.agent.group.agent_group import AgentGroup
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.group.coordinator_agent import CoordinatorAgent
from autobyteus.llm.models import LLMModel
from autobyteus.llm.rpa.gemini_llm import GeminiLLM
from autobyteus.llm.rpa.groq_llm import GroqLLM
import os
from autobyteus.llm.rpa.mistral_llm import MistralLLM
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch

@pytest.fixture
def agent_group():
    group = AgentGroup()

    # Set up ResearchAgent
    current_dir = os.path.dirname(os.path.abspath(__file__))
    research_prompt = os.path.join(current_dir, "research_agent.prompt")
    research_llm = GroqLLM(model=LLMModel.LLAMA_3_1_70B_VERSATILE)
    research_prompt = PromptBuilder().from_file(research_prompt)
    research_tools = [GoogleSearch()]
    research_agent = GroupAwareAgent("ResearchAgent", research_prompt, research_llm, research_tools)

    # Set up SummaryAgent
    summary_llm = GeminiLLM()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    summary_prompt = os.path.join(current_dir, "summary_agent.prompt")
    summary_prompt = PromptBuilder().from_file(summary_prompt)
    summary_agent = GroupAwareAgent("SummarizationAgent", summary_prompt, summary_llm, [])

    # Add agents to the group
    group.add_agent(research_agent)
    group.add_agent(summary_agent)

    # Set up CoordinationAgent
    coordinator_llm = MistralLLM(model=LLMModel.MISTRAL_LARGE)
    coordinator_tools = []  # The coordinator will use the SendMessageTo tool added by GroupAwareAgent

    coordinator_agent = CoordinatorAgent("CoordinationAgent", coordinator_llm, coordinator_tools)
    group.set_coordinator_agent(coordinator_agent)

    return group

@pytest.mark.asyncio
async def test_research_summary_workflow(agent_group):
    # Define the user task
    user_task = "please tell me what is the current temperature in Berlin"
    
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
    assert agent_group.get_agent("SummarizationAgent") is not None

