import pytest
import asyncio
from autobyteus.agent.agent import StandaloneAgent
from autobyteus.conversation.user_message import UserMessage
from autobyteus.events.event_types import EventType

@pytest.mark.asyncio
async def test_agent_event_emission(mock_llm, mock_tools):
    # Track emitted events
    received_events = []
    
    def event_handler(agent_id, response):
        received_events.append((agent_id, response))
    
    initial_message = UserMessage(content="Hello")
    agent = StandaloneAgent(
        role="test_agent",
        llm=mock_llm,
        tools=mock_tools,
        initial_user_message=initial_message
    )
    
    agent.subscribe(EventType.ASSISTANT_RESPONSE, event_handler)
    
    # Start agent
    agent.start()
    await asyncio.sleep(0.1)
    
    # Send message to trigger event
    test_message = UserMessage(content="Test message")
    await agent.receive_user_message(test_message)
    
    await asyncio.sleep(0.2)
    
    # Verify events were emitted
    assert len(received_events) > 0
    assert received_events[0][0] == agent.agent_id
    
    # Cleanup
    agent.stop()
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_task_completion_event(mock_llm, mock_tools):
    initial_message = UserMessage(content="Hello")
    agent = StandaloneAgent(
        role="test_agent",
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