# file: autobyteus/tests/unit_tests/workflow/streaming/test_workflow_event_notifier.py
import pytest
from unittest.mock import MagicMock, patch

from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier
from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent, AgentEventRebroadcastPayload, WorkflowStatusUpdateData
from autobyteus.events.event_types import EventType
from autobyteus.workflow.status.workflow_status import WorkflowStatus
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType

@pytest.fixture
def notifier():
    mock_runtime = MagicMock()
    return WorkflowExternalEventNotifier(workflow_id="wf-123", runtime_ref=mock_runtime)

def test_notify_status_updated(notifier: WorkflowExternalEventNotifier):
    """Tests that notify_status_updated creates and emits a correct WORKFLOW event."""
    with patch.object(notifier, 'emit') as mock_emit:
        notifier.notify_status_updated(
            new_status=WorkflowStatus.IDLE,
            old_status=WorkflowStatus.BOOTSTRAPPING,
            extra_data={"error_message": "An error"}
        )
        
        mock_emit.assert_called_once()
        emitted_event = mock_emit.call_args.kwargs['payload']
        
        assert isinstance(emitted_event, WorkflowStreamEvent)
        assert emitted_event.workflow_id == "wf-123"
        assert emitted_event.event_source_type == "WORKFLOW"
        
        data = emitted_event.data
        assert isinstance(data, WorkflowStatusUpdateData)
        assert data.new_status == WorkflowStatus.IDLE
        assert data.old_status == WorkflowStatus.BOOTSTRAPPING
        assert data.error_message == "An error"

def test_publish_agent_event(notifier: WorkflowExternalEventNotifier):
    """Tests that publish_agent_event creates and emits a correct AGENT event."""
    agent_name = "Researcher"
    # FIX: Provide a valid data dictionary for the AssistantChunkData model to avoid validation errors.
    mock_agent_event_data = {"content": "chunk text", "is_complete": False}
    mock_agent_event = StreamEvent(
        agent_id="agent-abc", 
        event_type=StreamEventType.ASSISTANT_CHUNK, 
        data=mock_agent_event_data
    )

    with patch.object(notifier, 'emit') as mock_emit:
        notifier.publish_agent_event(agent_name, mock_agent_event)
        
        mock_emit.assert_called_once()
        emitted_event = mock_emit.call_args.kwargs['payload']
        
        assert isinstance(emitted_event, WorkflowStreamEvent)
        assert emitted_event.workflow_id == "wf-123"
        assert emitted_event.event_source_type == "AGENT"
        
        data = emitted_event.data
        assert isinstance(data, AgentEventRebroadcastPayload)
        assert data.agent_name == agent_name
        assert data.agent_event == mock_agent_event
