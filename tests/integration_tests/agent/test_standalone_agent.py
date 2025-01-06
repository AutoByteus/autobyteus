
import pytest
import asyncio
from autobyteus.agent.agent import Agent
from autobyteus.conversation.user_message import UserMessage
from autobyteus.events.event_types import EventType
from autobyteus.agent.status import AgentStatus

@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function to avoid scope warnings."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
async def test_agent_initialization(mock_llm, mock_tools):
    initial_message = UserMessage(content="Hello")
    agent = Agent(
        role="test_agent",

        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    assert agent.role == "test_agent"
    assert agent.status == AgentStatus.NOT_STARTED
    assert agent.tools == mock_tools
    assert agent._queues_initialized is False

@pytest.mark.asyncio
async def test_agent_lifecycle(mock_llm, mock_tools):
    initial_message = UserMessage(content="Hello")
    agent = Agent(
        role="test_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    agent.start()
    await asyncio.sleep(0.2)  # Increased sleep time to allow agent to start

    assert agent.status == AgentStatus.RUNNING
    
    agent.stop()
    await asyncio.sleep(0.2)  # Allow time for the agent to stop

    assert agent.status == AgentStatus.ENDED

@pytest.mark.asyncio
async def test_agent_message_handling(mock_llm, mock_tools):
    mock_llm.responses = [
        "Initial response",
        """<command name="mock_tool">
            <arg name="arg1">test</arg>
        </command>"""
    ]
    
    initial_message = UserMessage(content="Hello")
    agent = Agent(
        role="test_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    received_events = []
    def event_handler(response, **kwargs):
        received_events.append((response))
    
    agent.subscribe(EventType.ASSISTANT_RESPONSE, event_handler)
    
    agent.start()
    await asyncio.sleep(0.2)  # Allow agent to start and process initial message
    
    test_message = UserMessage(content="Test message")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(0.5)  # Allow time for message handling
    
    assert len(received_events) > 0
    assert mock_tools[0].execution_count > 0
    
    agent.stop()
    await asyncio.sleep(0.2)

@pytest.mark.asyncio
async def test_agent_tool_execution(mock_llm, mock_tools):
    mock_llm.responses = [
        "Initial response",
        """<command name="mock_tool">
            <arg name="arg1">test_value</arg>
        </command>"""
    ]
    
    initial_message = UserMessage(content="Hello")
    agent = Agent(
        role="test_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    agent.start()
    await asyncio.sleep(0.2)  # Allow agent to start and process initial message
    
    test_message = UserMessage(content="Test message")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(0.5)  # Allow time for tool execution
    
    assert mock_tools[0].execution_count > 0
    assert mock_tools[0].last_args == {"arg1": "test_value"}
    
    agent.stop()
    await asyncio.sleep(0.2)

@pytest.mark.asyncio
async def test_agent_error_handling(mock_llm, mock_tools):
    async def error_execute(**kwargs):
        raise Exception("Test error")
    
    mock_tools[0]._execute = error_execute
    
    mock_llm.responses = [
        "Initial response",
        """<command name="mock_tool">
            <arg name="arg1">test</arg>
        </command>"""
    ]
    
    initial_message = UserMessage(content="Hello")
    agent = Agent(
        role="test_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    error_handled = False
    async def check_error_message(message):
        nonlocal error_handled
        if "Error:" in message:
            error_handled = True
    
    original_put = agent.tool_result_messages.put
    agent.tool_result_messages.put = check_error_message
    
    agent.start()
    await asyncio.sleep(0.2)  # Allow agent to start and process initial message
    
    test_message = UserMessage(content="Test message")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(0.5)  # Allow time for error handling
    
    assert error_handled
    
    agent.stop()
    await asyncio.sleep(0.2)
