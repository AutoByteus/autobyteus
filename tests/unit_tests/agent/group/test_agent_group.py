# File: tests/agent/group/test_agent_group.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator

from autobyteus.agent.group.agent_group import AgentGroup
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.group.coordinator_agent import CoordinatorAgent
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool

@pytest.fixture
def mock_llm() -> MagicMock:
    return MagicMock(spec=BaseLLM)

@pytest.fixture
def mock_tool() -> MagicMock:
    return MagicMock(spec=BaseTool)

@pytest.fixture
def agent_group() -> AgentGroup:
    return AgentGroup()

@pytest.mark.asyncio
async def test_agent_group_with_coordinator(
    agent_group: AgentGroup,
    mock_llm: MagicMock,
    mock_tool: MagicMock
) -> None:
    # Create mock agents
    mock_agent1: AsyncMock = AsyncMock(spec=GroupAwareAgent)
    mock_agent1.role = "Agent1"
    mock_agent1.run = AsyncMock()

    mock_agent2: AsyncMock = AsyncMock(spec=GroupAwareAgent)
    mock_agent2.role = "Agent2"
    mock_agent2.run = AsyncMock()

    # Create mock coordinator agent
    mock_coordinator: AsyncMock = AsyncMock(spec=CoordinatorAgent)
    mock_coordinator.role = "Coordinator"
    mock_coordinator.run = AsyncMock(return_value="Task completed")

    # Add agents to the group
    agent_group.add_agent(mock_agent1)
    agent_group.add_agent(mock_agent2)
    
    # Set coordinator agent
    agent_group.set_coordinator_agent(mock_coordinator)

    # Run the agent group
    result: str = await agent_group.run("Test task")

    # Assertions
    assert result == "Task completed"
    mock_coordinator.run.assert_called_once_with("Test task")
    mock_agent1.run.assert_called_once()
    mock_agent2.run.assert_called_once()
    assert len(agent_group.agents) == 3
    assert agent_group.coordinator_agent == mock_coordinator