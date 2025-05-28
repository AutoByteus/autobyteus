# file: autobyteus/tests/unit_tests/agent/events/test_agent_event_queues.py
import asyncio
import logging
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from autobyteus.agent.events.agent_event_queues import AgentEventQueues, END_OF_STREAM_SENTINEL
from autobyteus.agent.events.agent_events import (
    UserMessageReceivedEvent,
    InterAgentMessageReceivedEvent,
    PendingToolInvocationEvent,
    ToolResultEvent,
    ToolExecutionApprovalEvent,
    BaseEvent,
    ApprovedToolInvocationEvent, 
    GenericEvent,
    LLMUserMessageReadyEvent, # UPDATED from LLMPromptReadyEvent
    CreateToolInstancesEvent, # ADDED - New Preparation Event
    ProcessSystemPromptEvent, # ADDED - New Preparation Event
    FinalizeLLMConfigEvent,   # ADDED - New Preparation Event
    CreateLLMInstanceEvent    # ADDED - New Preparation Event
)
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.message.inter_agent_message import InterAgentMessage, InterAgentMessageType
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.user_message import LLMUserMessage # For LLMUserMessageReadyEvent payload

# Dummy event instances for testing
@pytest.fixture
def dummy_user_message_event():
    return UserMessageReceivedEvent(agent_input_user_message=AgentInputUserMessage(content="hello"))

@pytest.fixture
def dummy_inter_agent_message_event():
    return InterAgentMessageReceivedEvent(
        inter_agent_message=InterAgentMessage(
            recipient_role_name="test_receiver",
            recipient_agent_id="receiver_id_123",
            content="inter-agent hi",
            message_type=InterAgentMessageType.TASK_ASSIGNMENT,
            sender_agent_id="sender_id_456"
        )
    )

@pytest.fixture
def dummy_pending_tool_invocation_event():
    return PendingToolInvocationEvent(tool_invocation=ToolInvocation(name="test_tool", arguments={"arg1": "val1"}))

@pytest.fixture
def dummy_tool_result_event():
    return ToolResultEvent(tool_name="test_tool", result="success", tool_invocation_id="inv_123")

@pytest.fixture
def dummy_tool_approval_event():
    return ToolExecutionApprovalEvent(tool_invocation_id="inv_123", is_approved=True)

@pytest.fixture
def dummy_approved_tool_invocation_event():
    return ApprovedToolInvocationEvent(tool_invocation=ToolInvocation(name="approved_tool", arguments={"arg": "val"}))

@pytest.fixture
def dummy_generic_event():
    return GenericEvent(payload={"data": "test"}, type_name="dummy_generic")

@pytest.fixture
def dummy_llm_user_message_ready_event(): # UPDATED fixture name and type
    return LLMUserMessageReadyEvent(llm_user_message=LLMUserMessage(content="User prompt for LLM"))

# ADDED: Fixtures for new initialization events
@pytest.fixture
def dummy_create_tool_instances_event():
    return CreateToolInstancesEvent()

@pytest.fixture
def dummy_process_system_prompt_event():
    return ProcessSystemPromptEvent()

@pytest.fixture
def dummy_finalize_llm_config_event():
    return FinalizeLLMConfigEvent()

@pytest.fixture
def dummy_create_llm_instance_event():
    return CreateLLMInstanceEvent()


@pytest.mark.asyncio
class TestAgentEventQueues:

    @pytest.fixture
    def queues(self):
        return AgentEventQueues(queue_size=10) 

    def test_initialization(self, queues: AgentEventQueues):
        assert isinstance(queues.user_message_input_queue, asyncio.Queue)
        assert isinstance(queues.inter_agent_message_input_queue, asyncio.Queue)
        assert isinstance(queues.tool_invocation_request_queue, asyncio.Queue)
        assert isinstance(queues.tool_result_input_queue, asyncio.Queue)
        assert isinstance(queues.tool_execution_approval_queue, asyncio.Queue)
        assert isinstance(queues.internal_system_event_queue, asyncio.Queue)

        assert isinstance(queues.assistant_output_chunk_queue, asyncio.Queue)
        assert isinstance(queues.assistant_final_message_queue, asyncio.Queue)
        assert isinstance(queues.tool_interaction_log_queue, asyncio.Queue)

        assert len(queues._input_queues) == 6 
        input_queue_names = [name for name, _ in queues._input_queues]
        assert "user_message_input_queue" in input_queue_names
        assert "internal_system_event_queue" in input_queue_names 
        
        assert len(queues._output_queues_map) == 3 
        assert "assistant_output_chunk_queue" in queues._output_queues_map

    async def test_enqueue_user_message(self, queues: AgentEventQueues, dummy_user_message_event: UserMessageReceivedEvent):
        await queues.enqueue_user_message(dummy_user_message_event)
        assert queues.user_message_input_queue.qsize() == 1
        retrieved_event = await queues.user_message_input_queue.get()
        assert retrieved_event == dummy_user_message_event

    async def test_enqueue_inter_agent_message(self, queues: AgentEventQueues, dummy_inter_agent_message_event: InterAgentMessageReceivedEvent):
        await queues.enqueue_inter_agent_message(dummy_inter_agent_message_event)
        assert queues.inter_agent_message_input_queue.qsize() == 1
        retrieved_event = await queues.inter_agent_message_input_queue.get()
        assert retrieved_event == dummy_inter_agent_message_event
        
    async def test_enqueue_tool_invocation_request(self, queues: AgentEventQueues, dummy_pending_tool_invocation_event: PendingToolInvocationEvent):
        await queues.enqueue_tool_invocation_request(dummy_pending_tool_invocation_event)
        assert queues.tool_invocation_request_queue.qsize() == 1
        retrieved_event = await queues.tool_invocation_request_queue.get()
        assert retrieved_event == dummy_pending_tool_invocation_event

    async def test_enqueue_tool_result(self, queues: AgentEventQueues, dummy_tool_result_event: ToolResultEvent):
        await queues.enqueue_tool_result(dummy_tool_result_event)
        assert queues.tool_result_input_queue.qsize() == 1
        retrieved_event = await queues.tool_result_input_queue.get()
        assert retrieved_event == dummy_tool_result_event

    async def test_enqueue_tool_approval_event(self, queues: AgentEventQueues, dummy_tool_approval_event: ToolExecutionApprovalEvent):
        await queues.enqueue_tool_approval_event(dummy_tool_approval_event)
        assert queues.tool_execution_approval_queue.qsize() == 1
        retrieved_event = await queues.tool_execution_approval_queue.get()
        assert retrieved_event == dummy_tool_approval_event

    async def test_enqueue_internal_system_event(self, queues: AgentEventQueues, dummy_generic_event: GenericEvent):
        await queues.enqueue_internal_system_event(dummy_generic_event)
        assert queues.internal_system_event_queue.qsize() == 1
        retrieved_event = await queues.internal_system_event_queue.get()
        assert retrieved_event == dummy_generic_event

    async def test_enqueue_end_of_stream_sentinel_to_output_queue(self, queues: AgentEventQueues, caplog):
        target_queue_name = "assistant_final_message_queue"
        await queues.enqueue_end_of_stream_sentinel_to_output_queue(target_queue_name)
        target_queue = queues._output_queues_map[target_queue_name]
        assert target_queue.qsize() == 1
        sentinel = await target_queue.get()
        assert sentinel is END_OF_STREAM_SENTINEL

        caplog.set_level(logging.WARNING)
        caplog.clear()
        await queues.enqueue_end_of_stream_sentinel_to_output_queue("invalid_queue_name")
        assert "Attempted to enqueue END_OF_STREAM_SENTINEL to unknown output queue: invalid_queue_name" in caplog.text


    async def test_get_next_input_event_single_queue(self, queues: AgentEventQueues, dummy_user_message_event: UserMessageReceivedEvent):
        await queues.enqueue_user_message(dummy_user_message_event)
        result = await queues.get_next_input_event()
        assert result is not None
        queue_name, event = result
        assert queue_name == "user_message_input_queue"
        assert event == dummy_user_message_event

    async def test_get_next_input_event_multiple_queues(self, queues: AgentEventQueues, dummy_user_message_event: UserMessageReceivedEvent, dummy_tool_result_event: ToolResultEvent):
        # Enqueue in a specific order to make test deterministic if asyncio.wait behaves as LIFO for ready tasks (implementation detail)
        # but test should not rely on order.
        await queues.enqueue_tool_result(dummy_tool_result_event) 
        await queues.enqueue_user_message(dummy_user_message_event)
        
        result1 = await queues.get_next_input_event()
        assert result1 is not None
        queue_name1, event1 = result1
        
        result2 = await queues.get_next_input_event()
        assert result2 is not None
        queue_name2, event2 = result2

        results = [(queue_name1, event1), (queue_name2, event2)]

        expected_tool_result_tuple = ("tool_result_input_queue", dummy_tool_result_event)
        expected_user_message_tuple = ("user_message_input_queue", dummy_user_message_event)

        assert len(results) == 2
        # Check that both expected tuples are present in the results list
        # This does not rely on the order or hashability for set conversion.
        assert expected_tool_result_tuple in results
        assert expected_user_message_tuple in results
        
        assert queues.user_message_input_queue.empty()
        assert queues.tool_result_input_queue.empty()

    async def test_get_next_input_event_no_events(self, queues: AgentEventQueues):
        with pytest.raises(asyncio.TimeoutError): # Behavior of get_next_input_event is to block if no events
            await asyncio.wait_for(queues.get_next_input_event(), timeout=0.01)

    async def test_get_next_input_event_non_base_event_in_queue(self, queues: AgentEventQueues, caplog, dummy_llm_user_message_ready_event: LLMUserMessageReadyEvent):
        caplog.set_level(logging.ERROR)
        non_event_item = "this is not a BaseEvent"
        # Put the non-event item into a queue that get_next_input_event will check
        await queues.user_message_input_queue.put(non_event_item) # type: ignore
        
        # Put a valid event into another queue to ensure get_next_input_event can proceed and report the error.
        await queues.enqueue_internal_system_event(dummy_llm_user_message_ready_event)

        result = await queues.get_next_input_event() # This should pick up dummy_llm_user_message_ready_event
        assert result is not None
        queue_name, event = result
        
        # Verify error log for the bad item
        assert f"Dequeued item from user_message_input_queue is not a BaseEvent subclass: {type(non_event_item)}" in caplog.text
        # Verify the valid event was processed
        assert queue_name == "internal_system_event_queue" 
        assert event == dummy_llm_user_message_ready_event
        # The bad item should have been consumed and discarded by the error handling in get_next_input_event
        assert queues.user_message_input_queue.empty() 

    async def test_get_next_input_event_empty_tasks_list_if_no_input_queues(self, queues: AgentEventQueues):
        queues._input_queues = [] # Simulate no input queues configured
        result = await queues.get_next_input_event()
        assert result is None

    @patch('asyncio.Queue.join', new_callable=AsyncMock)
    async def test_graceful_shutdown(self, mock_join: AsyncMock, queues: AgentEventQueues, caplog, dummy_user_message_event: UserMessageReceivedEvent):
        caplog.set_level(logging.INFO)
        
        await queues.user_message_input_queue.put(dummy_user_message_event)
        
        await queues.graceful_shutdown(timeout=0.1)
        
        assert mock_join.call_count == len(queues._output_queues_map) 
        
        assert "Input queue 'user_message_input_queue' has 1 items remaining at shutdown." in caplog.text
        assert "AgentEventQueues graceful shutdown process (joining queues) completed." in caplog.text

    @patch('asyncio.Queue.join', new_callable=AsyncMock, side_effect=asyncio.TimeoutError)
    async def test_graceful_shutdown_timeout(self, mock_join_timeout: AsyncMock, queues: AgentEventQueues, caplog):
        caplog.set_level(logging.WARNING)
        await queues.graceful_shutdown(timeout=0.01)
        assert mock_join_timeout.call_count == len(queues._output_queues_map)
        assert "Timeout (0.01s) waiting for output queues to join during shutdown." in caplog.text

    async def test_get_next_input_event_task_cancellation_in_one_queue_task(self, queues: AgentEventQueues, dummy_user_message_event: UserMessageReceivedEvent, caplog, dummy_inter_agent_message_event: InterAgentMessageReceivedEvent):
        caplog.set_level(logging.DEBUG) # Set to DEBUG to see more detailed logs from get_next_input_event
        
        # Mock the 'get' method of one queue's task to raise CancelledError
        # This simulates that specific task being cancelled while asyncio.wait is active.
        # We need to ensure the logic in get_next_input_event correctly handles this.
        
        # We'll patch asyncio.create_task to intercept the task created for user_message_input_queue
        # and make its result() (or await) raise CancelledError.
        
        original_create_task = asyncio.create_task
        cancelled_task_name_check = "user_message_input_queue"
        simulated_cancelled_task_future = asyncio.Future()
        simulated_cancelled_task_future.set_exception(asyncio.CancelledError("Simulated cancellation of user_message_input_queue task"))

        def create_task_side_effect(coro, *, name=None):
            if name == cancelled_task_name_check:
                # This task will appear as done and cancelled when asyncio.wait checks it
                # To truly simulate a task being cancelled *during* the wait, this is tricky.
                # A simpler way is to make its .result() raise.
                # Let's instead patch the queue.get() for that specific queue.
                pass # Fall through to original logic as patching create_task for this is complex
            return original_create_task(coro, name=name)
        
        # Let's directly patch the .get() of the user_message_input_queue
        original_user_queue_get = queues.user_message_input_queue.get
        queues.user_message_input_queue.get = AsyncMock(side_effect=asyncio.CancelledError("Simulated cancellation for user_message_input_queue.get()"))

        # Enqueue events: one will hit the cancelled .get(), the other should proceed
        await queues.user_message_input_queue.put(dummy_user_message_event) # This will trigger the patched .get()
        await queues.inter_agent_message_input_queue.put(dummy_inter_agent_message_event) # This should be picked up

        result = await queues.get_next_input_event()
        
        assert result is not None, "Expected an event to be processed from the non-cancelled queue"
        queue_name, event = result

        # Check logs for cancellation of the first task (user_message_input_queue task)
        # The log message "Task for queue {queue_name} (from done set) was cancelled during result processing." or similar
        # is expected due to how get_next_input_event handles tasks from `done_tasks_from_wait`.
        assert any(
            f"Task for queue {cancelled_task_name_check}" in record.message and 
            ("was cancelled during result processing." in record.message or "Error processing result from task" in record.message) # Error msg could also indicate problem processing a cancelled task
            for record in caplog.records
        ), "Log message indicating cancellation/error for the user_message_input_queue task was not found."
        
        # The event from the non-cancelled queue should be returned
        assert queue_name == "inter_agent_message_input_queue"
        assert event == dummy_inter_agent_message_event
        
        # The mocked get should have been called
        queues.user_message_input_queue.get.assert_called_once()
        
        # Restore original get method
        queues.user_message_input_queue.get = original_user_queue_get

