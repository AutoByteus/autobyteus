import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent, AgentStatus
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent.message.message import Message
from autobyteus.agent.message.message_types import MessageType

@pytest.fixture
def mock_llm():
    return Mock()

@pytest.fixture
def mock_prompt_builder():
    return Mock()

@pytest.fixture
def mock_persistence_provider():
    return Mock()

@pytest.fixture
def group_aware_agent(mock_llm, mock_prompt_builder, mock_persistence_provider):
    return GroupAwareAgent(
        role="test_agent",
        prompt_builder=mock_prompt_builder,
        llm=mock_llm,
        tools=[],  # Empty list of tools for this test
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
    
    message = Message("test_agent", "test_agent_id", "test message", MessageType.TASK_ASSIGNMENT, "sender_id")
    await group_aware_agent.receive_agent_message(message)
    start_mock.assert_called_once()
    assert group_aware_agent.incoming_agent_messages.qsize() == 1

@pytest.mark.asyncio
async def test_receive_agent_message_running(group_aware_agent):
    group_aware_agent.status = AgentStatus.RUNNING
    message = Message("test_agent", "test_agent_id", "test message", MessageType.TASK_ASSIGNMENT, "sender_id")
    await group_aware_agent.receive_agent_message(message)
    assert group_aware_agent.incoming_agent_messages.qsize() == 1

@pytest.mark.asyncio
async def test_run(group_aware_agent, monkeypatch):
    initialize_mock = AsyncMock()
    handle_messages_mock = AsyncMock()
    handle_tool_results_mock = AsyncMock()
    cleanup_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "initialize_llm_conversation", initialize_mock)
    monkeypatch.setattr(group_aware_agent, "handle_agent_messages", handle_messages_mock)
    monkeypatch.setattr(group_aware_agent, "handle_tool_result_messages", handle_tool_results_mock)
    monkeypatch.setattr(group_aware_agent, "cleanup", cleanup_mock)

    # Set the task_completed event after a short delay
    async def set_task_completed():
        await asyncio.sleep(0.1)
        group_aware_agent.task_completed.set()

    asyncio.create_task(set_task_completed())

    await group_aware_agent.run()
    
    initialize_mock.assert_called_once()
    handle_messages_mock.assert_called_once()
    handle_tool_results_mock.assert_called_once()
    cleanup_mock.assert_called_once()
    assert group_aware_agent.status == AgentStatus.ENDED

@pytest.mark.asyncio
async def test_handle_agent_messages(group_aware_agent, monkeypatch):
    mock_conversation = AsyncMock()
    mock_conversation.send_user_message = AsyncMock(return_value="LLM response")
    group_aware_agent.conversation = mock_conversation

    process_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "process_llm_response", process_mock)
    group_aware_agent.status = AgentStatus.RUNNING
    message = Message("test_agent", "test_agent_id", "test message", MessageType.TASK_ASSIGNMENT, "sender_id")
    await group_aware_agent.incoming_agent_messages.put(message)

    # Set the task_completed event after a short delay
    async def set_task_completed():
        await asyncio.sleep(0.1)
        group_aware_agent.task_completed.set()

    asyncio.create_task(set_task_completed())

    await group_aware_agent.handle_agent_messages()

    mock_conversation.send_user_message.assert_called_once_with("Message from sender_id: test message")
    process_mock.assert_called_once_with("LLM response")

@pytest.mark.asyncio
async def test_handle_tool_result_messages(group_aware_agent, monkeypatch):
    mock_conversation = AsyncMock()
    mock_conversation.send_user_message = AsyncMock(return_value="LLM response")
    group_aware_agent.conversation = mock_conversation

    process_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "process_llm_response", process_mock)
    group_aware_agent.status = AgentStatus.RUNNING
    await group_aware_agent.tool_result_messages.put("test result")

    # Set the task_completed event after a short delay
    async def set_task_completed():
        await asyncio.sleep(0.1)
        group_aware_agent.task_completed.set()

    asyncio.create_task(set_task_completed())

    await group_aware_agent.handle_tool_result_messages()

    mock_conversation.send_user_message.assert_called_once_with("Tool execution result: test result")
    process_mock.assert_called_once_with("LLM response")

@pytest.mark.asyncio
async def test_process_llm_response_valid_tool(group_aware_agent, monkeypatch):
    mock_tool_invocation = Mock(is_valid=lambda: True, name="MockTool", arguments={})
    
    # Create a mock response parser
    mock_response_parser = Mock()
    mock_response_parser.parse_response.return_value = mock_tool_invocation
    
    # Replace the response_parser with our mock
    monkeypatch.setattr(group_aware_agent, "response_parser", mock_response_parser)
    
    execute_mock = AsyncMock()
    monkeypatch.setattr(group_aware_agent, "execute_tool", execute_mock)

    await group_aware_agent.process_llm_response("test response")
    
    mock_response_parser.parse_response.assert_called_once_with("test response")
    execute_mock.assert_called_once_with(mock_tool_invocation)

@pytest.mark.asyncio
async def test_process_llm_response_invalid_tool(group_aware_agent, monkeypatch, caplog):
    mock_tool_invocation = Mock(is_valid=lambda: False)
    
    # Create a mock response parser
    mock_response_parser = Mock()
    mock_response_parser.parse_response.return_value = mock_tool_invocation
    
    # Replace the response_parser with our mock
    monkeypatch.setattr(group_aware_agent, "response_parser", mock_response_parser)

    await group_aware_agent.process_llm_response("test response")
    
    mock_response_parser.parse_response.assert_called_once_with("test response")
    assert "LLM Response: test response" in caplog.text

@pytest.mark.asyncio
async def test_execute_tool(group_aware_agent):
    mock_tool = AsyncMock()
    mock_tool.__class__.__name__ = "MockTool"
    mock_tool.execute = AsyncMock(return_value="Tool execution result")
    group_aware_agent.tools.append(mock_tool)

    #