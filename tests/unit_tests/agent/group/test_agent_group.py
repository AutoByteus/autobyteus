# File: tests/unit_tests/agent/group/test_agent_group.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from autobyteus.agent.group.single_replica_agent_orchestrator import SingleReplicaAgentOrchestrator
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
def agent_group() -> SingleReplicaAgentOrchestrator:
    return SingleReplicaAgentOrchestrator()

@pytest.mark.asyncio
async def test_agent_group_with_coordinator(
    agent_group: SingleReplicaAgentOrchestrator,
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
    mock_agent1.run.assert_not_called()
    mock_agent2.run.assert_not_called()
    assert len(agent_group.agents) == 3
    assert agent_group.coordinator_agent == mock_coordinator

@pytest.mark.asyncio
async def test_agent_group_with_start_agent(
    agent_group: SingleReplicaAgentOrchestrator,
    mock_llm: MagicMock,
    mock_tool: MagicMock
) -> None:
    # Create mock agents
    mock_start_agent: AsyncMock = AsyncMock(spec=GroupAwareAgent)
    mock_start_agent.role = "StartAgent"
    mock_start_agent.run = AsyncMock(return_value="Task completed")

    mock_agent2: AsyncMock = AsyncMock(spec=GroupAwareAgent)
    mock_agent2.role = "Agent2"
    mock_agent2.run = AsyncMock()

    # Add agents to the group
    agent_group.add_agent(mock_start_agent)
    agent_group.add_agent(mock_agent2)
    
    # Set start agent
    agent_group.set_start_agent(mock_start_agent)

    # Run the agent group
    result: str = await agent_group.run()

    # Assertions
    assert result == "Task completed"
    mock_start_agent.run.assert_called_once()
    mock_agent2.run.assert_not_called()
    assert len(agent_group.agents) == 2
    assert agent_group.start_agent == mock_start_agent

@pytest.mark.asyncio
async def test_agent_group_no_lead_agent(agent_group: SingleReplicaAgentOrchestrator) -> None:
    with pytest.raises(ValueError, match="Neither coordinator agent nor start agent set"):
        await agent_group.run()

@pytest.mark.asyncio
async def test_route_message(agent_group: SingleReplicaAgentOrchestrator) -> None:
    mock_agent1: AsyncMock = AsyncMock(spec=GroupAwareAgent)
    mock_agent1.role = "Agent1"
    mock_agent1.receive_agent_message = AsyncMock(return_value="Message received")

    agent_group.add_agent(mock_agent1)

    result = await agent_group.route_message("SenderAgent", "Agent1", "Test message")

    assert result == "Message received"
    mock_agent1.receive_agent_message.assert_called_once_with("SenderAgent", "Test message")

@pytest.mark.asyncio
async def test_route_message_invalid_agent(agent_group: SingleReplicaAgentOrchestrator) -> None:
    result = await agent_group.route_message("SenderAgent", "InvalidAgent", "Test message")

    assert result == "Error: Agent with role 'InvalidAgent' not found."