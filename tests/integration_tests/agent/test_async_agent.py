import pytest
import asyncio
from autobyteus.agent.async_agent import AsyncAgent
from autobyteus.conversation.user_message import UserMessage
from autobyteus.events.event_types import EventType
from autobyteus.agent.status import AgentStatus

@pytest.mark.asyncio
async def test_async_agent_initialization(mock_llm, mock_tools):
    initial_message = UserMessage(content="Hello AsyncAgent")
    agent = AsyncAgent(
        role="test_async_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    assert agent.role == "test_async_agent"
    assert agent.status == AgentStatus.NOT_STARTED
    assert agent.tools == mock_tools
    assert agent._queues_initialized is False

@pytest.mark.asyncio
async def test_async_agent_lifecycle(mock_llm, mock_tools):
    initial_message = UserMessage(content="Hello AsyncAgent")
    agent = AsyncAgent(
        role="test_async_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    agent.start()
    await asyncio.sleep(0.1)
    assert agent.status == AgentStatus.RUNNING
    
    agent.stop()
    await asyncio.sleep(0.1)
    assert agent.status == AgentStatus.ENDED

@pytest.mark.asyncio
async def test_async_agent_message_handling(mock_llm, mock_tools):
    mock_llm.responses = [
        "Initial async response",
        """<command name="mock_tool">
            <arg name="arg1">async_test</arg>
        </command>"""
    ]
    
    initial_message = UserMessage(content="Hello AsyncAgent")
    agent = AsyncAgent(
        role="test_async_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    received_events = []
    def event_handler(agent_id, response, streaming=False):
        received_events.append((agent_id, response, streaming))
    
    agent.subscribe(EventType.ASSISTANT_RESPONSE, event_handler)
    
    agent.start()
    await asyncio.sleep(0.5)
    
    test_message = UserMessage(content="Test async message")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(1.0)
    
    assert len(received_events) > 0
    # Check that streaming responses were emitted
    streaming_responses = [event for event in received_events if event[2]]
    assert len(streaming_responses) > 0
    # Check that non-streaming complete response was emitted
    complete_responses = [event for event in received_events if not event[2]]
    assert len(complete_responses) > 0
    # Verify tool execution
    assert mock_tools[0].execution_count > 0
    
    agent.stop()
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_async_agent_tool_execution(mock_llm, mock_tools):
    mock_llm.responses = [
        "Initial async response",
        """<command name="mock_tool">
            <arg name="arg1">async_tool_test</arg>
        </command>"""
    ]
    
    initial_message = UserMessage(content="Hello AsyncAgent")
    agent = AsyncAgent(
        role="test_async_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    agent.start()
    await asyncio.sleep(0.5)
    
    test_message = UserMessage(content="Execute tool")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(1.0)
    
    assert mock_tools[0].execution_count > 0
    assert mock_tools[0].last_args == {"arg1": "async_tool_test"}
    
    agent.stop()
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_async_agent_error_handling(mock_llm, mock_tools):
    async def error_execute(**kwargs):
        raise Exception("Async test error")
    
    mock_tools[0]._execute = error_execute
    
    mock_llm.responses = [
        "Initial async response",
        """<command name="mock_tool">
            <arg name="arg1">error_test</arg>
        </command>"""
    ]
    
    initial_message = UserMessage(content="Hello AsyncAgent")
    agent = AsyncAgent(
        role="test_async_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    error_handled = False
    async def check_error_message(agent_id, response, streaming=False):
        nonlocal error_handled
        if "Error:" in response:
            error_handled = True
    
    agent.subscribe(EventType.ASSISTANT_RESPONSE, check_error_message)
    
    agent.start()
    await asyncio.sleep(0.2)
    
    test_message = UserMessage(content="Trigger error")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(1.0)
    
    assert error_handled
    
    agent.stop()
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_async_agent_event_emission(mock_llm, mock_tools):
    received_events = []
    
    def event_handler(agent_id, response, streaming=False):
        received_events.append((agent_id, response, streaming))
    
    initial_message = UserMessage(content="Hello AsyncAgent")
    agent = AsyncAgent(
        role="test_async_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    agent.subscribe(EventType.ASSISTANT_RESPONSE, event_handler)
    
    # Start agent
    agent.start()
    await asyncio.sleep(0.1)
    
    # Send message to trigger event
    test_message = UserMessage(content="Emit event")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(0.2)
    
    # Verify events were emitted
    assert len(received_events) > 0
    assert received_events[0][0] == agent.agent_id
    
    # Cleanup
    agent.stop()
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_async_agent_task_completion_event(mock_llm, mock_tools):
    initial_message = UserMessage(content="Hello AsyncAgent")
    agent = AsyncAgent(
        role="test_async_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    # Start agent
    agent.start()
    await asyncio.sleep(0.1)
    
    # Emit task completion event
    agent.emit(EventType.TASK_COMPLETED, agent_id=agent.agent_id)
    
    await asyncio.sleep(0.2)
    
    # Verify agent responded to completion event
    assert agent.task_completed.is_set()
    
    # Cleanup
    agent.stop()
    await asyncio.sleep(0.1)