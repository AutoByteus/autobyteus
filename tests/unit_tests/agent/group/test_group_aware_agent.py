# File: tests/unit_tests/agent/group/test_group_aware_agent.py

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent, AgentStatus
from autobyteus.agent.group.send_message_to import SendMessageTo

@pytest.fixture
def mock_llm():
    return Mock()

@pytest.fixture
def mock_conversation_manager():
    return AsyncMock()

@pytest.fixture
def mock_prompt_builder():
    return Mock()

@pytest.fixture
def mock_response_parser():
    return Mock()

@pytest.fixture
def mock_persistence_provider():
    return Mock()

@pytest.fixture
def group_aware_agent(mock_llm, mock_prompt_builder, mock_response_parser, mock_persistence_provider):
    return GroupAwareAgent(
        role="test_agent",
        prompt_builder=mock_prompt_builder,
        llm=mock_llm,
        tools=[],  # Empty list of tools for this test
        use_xml_parser=True,
        persistence_provider_class=mock_persistence_provider
    )

@pytest.mark.asyncio
async def test_initialization(group_aware_agent):
    assert group_aware_agent.status == AgentStatus.NOT_STARTED
    assert group_aware_agent.agent_group is None

@pytest.mark.asyncio
async def test_set_agent_group(group_aware_agent):
    mock_agent_group = Mock()
    group_aware_agent.set_agent_group(mock_agent_group)
    assert group_aware_agent.agent_group == mock_agent_group
    assert any(isinstance(tool, SendMessageTo) for tool in group_aware_agent.tools)

@pytest.mark.asyncio
async def test_receive_agent_message_not_started(group_aware_agent, monkeypatch):
    start_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "start", start_mock)
    
    await group_aware_agent.receive_agent_message("sender", "test message")
    start_mock.assert_called_once()
    assert group_aware_agent.incoming_agent_messages.qsize() == 1

@pytest.mark.asyncio
async def test_receive_agent_message_running(group_aware_agent):
    group_aware_agent.status = AgentStatus.RUNNING
    await group_aware_agent.receive_agent_message("sender", "test message")
    assert group_aware_agent.incoming_agent_messages.qsize() == 1

@pytest.mark.asyncio
async def test_run(group_aware_agent, monkeypatch):
    initialize_mock = AsyncMock()
    handle_messages_mock = AsyncMock()
    handle_results_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "initialize_llm_conversation", initialize_mock)
    monkeypatch.setattr(group_aware_agent, "handle_agent_messages", handle_messages_mock)
    monkeypatch.setattr(group_aware_agent, "handle_tool_results", handle_results_mock)

    await group_aware_agent.run()
    
    initialize_mock.assert_called_once()
    handle_messages_mock.assert_called_once()
    handle_results_mock.assert_called_once()
    assert group_aware_agent.status == AgentStatus.ENDED


@pytest.mark.asyncio
async def test_handle_agent_messages(group_aware_agent, monkeypatch):
    # Mock the conversation
    mock_conversation = AsyncMock()
    mock_conversation.send_user_message = AsyncMock(return_value="LLM response")
    group_aware_agent.conversation = mock_conversation

    process_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "process_llm_response", process_mock)
    group_aware_agent.status = AgentStatus.RUNNING
    await group_aware_agent.incoming_agent_messages.put(("sender", "test message"))

    handle_task = asyncio.create_task(group_aware_agent.handle_agent_messages())
    await asyncio.sleep(0.1)  # Allow time for the message to be processed
    group_aware_agent.status = AgentStatus.ENDED  # Stop the loop
    await handle_task

    mock_conversation.send_user_message.assert_called_once_with("Message from sender: test message")
    process_mock.assert_called_once_with("LLM response")

@pytest.mark.asyncio
async def test_handle_tool_results(group_aware_agent, monkeypatch):
    # Mock the conversation
    mock_conversation = AsyncMock()
    mock_conversation.send_user_message = AsyncMock(return_value="LLM response")
    group_aware_agent.conversation = mock_conversation

    process_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "process_llm_response", process_mock)
    group_aware_agent.status = AgentStatus.RUNNING
    await group_aware_agent.tool_execution_results.put("test result")

    handle_task = asyncio.create_task(group_aware_agent.handle_tool_results())
    await asyncio.sleep(0.1)  # Allow time for the result to be processed
    group_aware_agent.status = AgentStatus.ENDED  # Stop the loop
    await handle_task

    mock_conversation.send_user_message.assert_called_once_with("Tool execution result: test result")
    process_mock.assert_called_once_with("LLM response")

@pytest.mark.asyncio
async def test_process_llm_response_valid_tool(group_aware_agent, monkeypatch):
    mock_tool_invocation = Mock(is_valid=lambda: True, name="MockTool", arguments={})
    group_aware_agent.response_parser.parse_response.return_value = mock_tool_invocation
    
    execute_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "execute_tool", execute_mock)

    await group_aware_agent.process_llm_response("test response")
    execute_mock.assert_called_once_with(mock_tool_invocation)

@pytest.mark.asyncio
async def test_process_llm_response_invalid_tool(group_aware_agent, caplog):
    mock_tool_invocation = Mock(is_valid=lambda: False)
    group_aware_agent.response_parser.parse_response.return_value = mock_tool_invocation

    await group_aware_agent.process_llm_response("test response")
    assert "LLM Response: test response" in caplog.text

@pytest.mark.asyncio
async def test_execute_tool(group_aware_agent):
    mock_tool = AsyncMock()
    mock_tool.__class__.__name__ = "MockTool"
    group_aware_agent.tools.append(mock_tool)

    mock_tool_invocation = Mock(name="MockTool", arguments={"arg": "value"})
    await group_aware_agent.execute_tool(mock_tool_invocation)

    mock_tool.execute.assert_called_once_with(arg="value")
    assert group_aware_agent.tool_execution_results.qsize() == 1

def test_get_description(group_aware_agent):
    tool1 = Mock()
    tool1.__class__.__name__ = "Tool1"
    tool2 = Mock()
    tool2.__class__.__name__ = "Tool2"
    group_aware_agent.tools = [tool1, tool2]
    description = group_aware_agent.get_description()
    assert "test_agent" in description
    assert "Tool1" in description
    assert "Tool2" in description

def test_get_status(group_aware_agent):
    assert group_aware_agent.get_status() == AgentStatus.NOT_STARTED
    group_aware_agent.status = AgentStatus.RUNNING
    assert group_aware_agent.get_status() == AgentStatus.RUNNING